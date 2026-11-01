package com.iot.thingmodel.product;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.iot.thingmodel.admin.TenantAccountService;
import com.iot.thingmodel.common.ApiException;
import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.sync.SyncResult;
import com.iot.thingmodel.sync.TbProductResourceDeleter;
import com.iot.thingmodel.sync.TbProfileSyncer;
import com.iot.thingmodel.sync.TbSyncRequest;
import com.iot.thingmodel.tb.TbSyncException;
import com.iot.thingmodel.tsl.CompactSchema;
import com.iot.thingmodel.tsl.TslAction;
import com.iot.thingmodel.tsl.TslDefinition;
import com.iot.thingmodel.tsl.TslEvent;
import com.iot.thingmodel.tsl.TslParser;
import com.iot.thingmodel.tsl.TslProperty;
import com.iot.thingmodel.tsl.TslValidator;
import com.iot.thingmodel.tsl.ValidationResult;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class ProductService {

    private final ProductRepository repository;
    private final TslParser parser;
    private final TslValidator validator;
    private final CompactSchema compactSchema;
    private final TbProfileSyncer syncer;
    private final TbProductResourceDeleter resourceDeleter;
    private final TenantAccountService tenantAccountService;
    private final ObjectMapper objectMapper;

    public ProductService(
            ProductRepository repository,
            TslParser parser,
            TslValidator validator,
            CompactSchema compactSchema,
            TbProfileSyncer syncer,
            TbProductResourceDeleter resourceDeleter,
            TenantAccountService tenantAccountService,
            ObjectMapper objectMapper) {
        this.repository = repository;
        this.parser = parser;
        this.validator = validator;
        this.compactSchema = compactSchema;
        this.syncer = syncer;
        this.resourceDeleter = resourceDeleter;
        this.tenantAccountService = tenantAccountService;
        this.objectMapper = objectMapper;
    }

    public List<ProductItem> list(UUID tenantId, String keyword) {
        return repository.listProducts(tenantId, keyword);
    }

    public ProductDetail get(UUID tenantId, String productId) {
        ProductRepository.ProductRow product = requireProduct(tenantId, productId);
        ProductRepository.TslRow latest = repository.findLatestTsl(tenantId, productId).orElse(null);
        List<ProductDetail.TslVersionView> versions = repository.listVersions(tenantId, productId);
        CatalogView catalog = null;
        TslDefinition definition = null;
        if (latest != null) {
            definition = parser.parse(latest.tsl());
            catalog = catalog(definition, latest.version());
        }
        ProductRepository.BindingRow binding = latest == null ? null
                : repository.findBinding(tenantId, productId, latest.version()).orElse(null);
        return new ProductDetail(toItem(product, latest, definition, binding), versions, catalog);
    }

    public ProductResponse create(CreateProductCommand command) {
        if (command.tenantId() == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TENANT_ID_REQUIRED, "缺少租户 ID");
        }
        JsonNode root = readTsl(command.tsl());
        if (root == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_REQUIRED, "缺少物模型 TSL");
        }
        TslDefinition definition = parser.parse(root);
        ValidationResult validation = validator.validate(root);
        if (!validation.valid()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_INVALID, "物模型校验失败", validation.errors());
        }

        String productId = firstNonBlank(command.productId(), definition.productId());
        if (productId == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.PRODUCT_ID_MISSING, "缺少 ProductId");
        }
        if (command.productId() != null && definition.productId() != null
                && !command.productId().equals(definition.productId())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.PRODUCT_ID_MISMATCH, "请求 ProductId 与 TSL 不一致");
        }

        String version = firstNonBlank(command.tslVersion(), definition.version());
        if (version == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.VERSION_MISSING, "缺少 TSL 版本");
        }
        if (command.tslVersion() != null && definition.version() != null
                && !command.tslVersion().equals(definition.version())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.VERSION_MISMATCH, "请求 TSL 版本与 TSL 内容不一致");
        }

        String name = firstNonBlank(command.name(), productId);
        String model = firstNonBlank(command.model(), productId);
        String categoryId = firstNonBlank(command.categoryId(), definition.categoryId());
        boolean strictUnknown = command.strictUnknown();
        String checksum = checksum(root);

        tenantAccountService.requireConfigured(command.tenantId());

        ProductRepository.DraftResult draft = repository.saveDraft(
                command.tenantId(),
                productId,
                name,
                model,
                categoryId,
                null,
                version,
                checksum,
                strictUnknown,
                root);

        CompactSchema.CompactResult compact = compactSchema.generate(definition, strictUnknown);
        SyncResult sync = runSync(new TbSyncRequest(
                command.tenantId(),
                productId,
                name,
                model,
                categoryId,
                version,
                root,
                definition,
                compact),
                productId,
                version);

        repository.publish(
                command.tenantId(),
                productId,
                version,
                definition,
                Constants.Tsl.SCHEMA_VERSION,
                sync.profileId(),
                sync.assetId(),
                sync.ruleChainId(),
                Constants.Product.SYNC_RESULT_OK);

        return new ProductResponse(
                productId,
                version,
                sync.profileId().toString(),
                sync.assetId().toString(),
                sync.ruleChainId() == null ? null : sync.ruleChainId().toString(),
                definition.properties().size(),
                definition.events().size(),
                definition.actions().size(),
                sync.schemaBytes(),
                Constants.Product.STATUS_PUBLISHED,
                validation.warnings());
    }

    public ProductResponse updateThingModel(
            UUID tenantId, String productId, UpdateThingModelRequest request) {
        ProductRepository.ProductRow product = requireProduct(tenantId, productId);
        JsonNode root = readTsl(request.tsl());
        if (root == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_REQUIRED, "缺少物模型 TSL");
        }
        TslDefinition definition = parser.parse(root);
        String version = firstNonBlank(request.tslVersion(), definition.version());
        if (version == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.VERSION_MISSING, "缺少 TSL 版本");
        }
        return create(new CreateProductCommand(
                product.tenantId(),
                product.productId(),
                product.name(),
                product.model(),
                product.categoryId(),
                version,
                root,
                Boolean.TRUE.equals(request.strictUnknown())));
    }

    public ValidationResponse validate(UUID tenantId, String productId, JsonNode body) {
        repository.findProduct(tenantId, productId);
        JsonNode root = body != null && body.has(Constants.Tsl.KEY_REQUEST_TSL)
                ? body.get(Constants.Tsl.KEY_REQUEST_TSL)
                : body;
        root = readTsl(root);
        if (root == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_REQUIRED, "缺少物模型 TSL");
        }
        ValidationResult result = validator.validate(root);
        return new ValidationResponse(result.valid(), result.errors(), result.warnings());
    }

    public ThingModelView getThingModel(UUID tenantId, String productId) {
        requireProduct(tenantId, productId);
        ProductRepository.TslRow tsl = repository.findLatestTsl(tenantId, productId)
                .orElseThrow(() -> new ApiException(
                        HttpStatus.NOT_FOUND,
                        Constants.ErrorCode.TSL_NOT_FOUND,
                        "产品尚未提交物模型"));
        return new ThingModelView(
                productId,
                tsl.version(),
                tsl.status(),
                tsl.strictUnknown(),
                tsl.tsl());
    }

    public ProductResponse sync(UUID tenantId, String productId) {
        ProductRepository.ProductRow product = requireProduct(tenantId, productId);
        ProductRepository.TslRow tsl = repository.findLatestTsl(tenantId, productId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, Constants.ErrorCode.TSL_NOT_FOUND, "产品尚未提交物模型"));
        TslDefinition definition = parser.parse(tsl.tsl());
        ValidationResult validation = validator.validate(tsl.tsl());
        if (!validation.valid()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_INVALID, "已存物模型校验失败", validation.errors());
        }
        CompactSchema.CompactResult compact = compactSchema.generate(definition, tsl.strictUnknown());
        SyncResult sync = runSync(new TbSyncRequest(
                product.tenantId(),
                product.productId(),
                product.name(),
                product.model(),
                product.categoryId(),
                tsl.version(),
                tsl.tsl(),
                definition,
                compact),
                productId,
                tsl.version());
        repository.publish(
                tenantId,
                productId,
                tsl.version(),
                definition,
                Constants.Tsl.SCHEMA_VERSION,
                sync.profileId(),
                sync.assetId(),
                sync.ruleChainId(),
                Constants.Product.SYNC_RESULT_OK);
        return new ProductResponse(
                productId,
                tsl.version(),
                sync.profileId().toString(),
                sync.assetId().toString(),
                sync.ruleChainId() == null ? null : sync.ruleChainId().toString(),
                definition.properties().size(),
                definition.events().size(),
                definition.actions().size(),
                sync.schemaBytes(),
                Constants.Product.STATUS_PUBLISHED,
                validation.warnings());
    }

    public void delete(UUID tenantId, String productId) {
        requireProduct(tenantId, productId);
        List<ProductRepository.BindingRow> bindings =
                repository.listBindings(tenantId, productId);
        List<ProductRepository.BindingRow> otherBindings =
                repository.listBindingsExcludingProduct(tenantId, productId);
        bindings = bindings == null ? List.of() : bindings;
        otherBindings = otherBindings == null ? List.of() : otherBindings;

        Set<UUID> profileIds = ownedIds(
                bindings, otherBindings, ProductRepository.BindingRow::profileId);
        Set<UUID> assetIds = ownedIds(
                bindings, otherBindings, ProductRepository.BindingRow::assetId);
        Set<UUID> ruleChainIds = ownedIds(
                bindings, otherBindings, ProductRepository.BindingRow::ruleChainId);

        try {
            if (!profileIds.isEmpty()) {
                long deviceCount = resourceDeleter.countDevices(tenantId, profileIds);
                if (deviceCount > Constants.Db.ZERO_COUNT) {
                    throw new ApiException(
                            HttpStatus.CONFLICT,
                            Constants.ErrorCode.PRODUCT_HAS_DEVICES,
                            "产品下存在 " + deviceCount + " 台设备，无法删除");
                }
            }
            resourceDeleter.deleteResources(tenantId, profileIds, assetIds, ruleChainIds);
        } catch (TbSyncException ex) {
            throw new ApiException(
                    HttpStatus.BAD_GATEWAY,
                    Constants.ErrorCode.TB_DELETE_FAILED,
                    ex.getMessage());
        }

        int deleted = repository.deleteProduct(tenantId, productId);
        if (deleted == Constants.Db.NO_ROWS_AFFECTED) {
            throw new ApiException(
                    HttpStatus.NOT_FOUND,
                    Constants.ErrorCode.PRODUCT_NOT_FOUND,
                    "产品不存在");
        }
    }

    public CatalogView catalog(UUID tenantId, String productId) {
        requireProduct(tenantId, productId);
        ProductRepository.TslRow latest = repository.findLatestTsl(tenantId, productId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, Constants.ErrorCode.TSL_NOT_FOUND, "产品尚未提交物模型"));
        return catalog(parser.parse(latest.tsl()), latest.version());
    }

    private SyncResult runSync(TbSyncRequest request, String productId, String version) {
        try {
            return syncer.sync(request);
        } catch (TbSyncException ex) {
            repository.recordSyncFailure(request.tenantId(), productId, version, ex.getMessage());
            throw new ApiException(
                    HttpStatus.BAD_GATEWAY,
                    Constants.ErrorCode.TB_SYNC_FAILED,
                    ex.getMessage(),
                    List.of(),
                    String.format(Constants.Api.PRODUCT_SYNC_RETRY_PATH, productId));
        } catch (ApiException ex) {
            repository.recordSyncFailure(request.tenantId(), productId, version, ex.getMessage());
            if (ex.getStatus() == HttpStatus.BAD_GATEWAY
                    && Constants.ErrorCode.TB_LOGIN_FAILED.equals(ex.getCode())) {
                throw new ApiException(
                        HttpStatus.BAD_GATEWAY,
                        Constants.ErrorCode.TB_SYNC_FAILED,
                        ex.getMessage(),
                        List.of(),
                        String.format(Constants.Api.PRODUCT_SYNC_RETRY_PATH, productId));
            }
            throw ex;
        }
    }

    private Set<UUID> ownedIds(
            List<ProductRepository.BindingRow> bindings,
            List<ProductRepository.BindingRow> otherBindings,
            Function<ProductRepository.BindingRow, UUID> extractor) {
        Set<UUID> shared = otherBindings.stream()
                .map(extractor)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        return bindings.stream()
                .map(extractor)
                .filter(Objects::nonNull)
                .filter(id -> !shared.contains(id))
                .collect(Collectors.toSet());
    }

    private ProductRepository.ProductRow requireProduct(UUID tenantId, String productId) {
        return repository.findProduct(tenantId, productId)
                .orElseThrow(() -> new ApiException(
                        HttpStatus.NOT_FOUND, Constants.ErrorCode.PRODUCT_NOT_FOUND, "产品不存在"));
    }


    private JsonNode readTsl(JsonNode tsl) {
        if (tsl == null || tsl.isNull()) {
            return null;
        }
        if (tsl.isTextual()) {
            try {
                return objectMapper.readTree(tsl.asText());
            } catch (Exception ex) {
                throw new ApiException(HttpStatus.BAD_REQUEST, Constants.ErrorCode.TSL_INVALID, "物模型不是合法 JSON");
            }
        }
        return tsl;
    }

    private String checksum(JsonNode root) {
        try {
            byte[] bytes = objectMapper.writeValueAsString(root).getBytes(StandardCharsets.UTF_8);
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance(Constants.Auth.SHA_256).digest(bytes));
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to calculate TSL checksum", ex);
        }
    }

    private ProductItem toItem(
            ProductRepository.ProductRow product,
            ProductRepository.TslRow latest,
            TslDefinition definition,
            ProductRepository.BindingRow binding) {
        long properties = definition == null
                ? Constants.Db.ZERO_COUNT
                : definition.properties().size();
        long events = definition == null
                ? Constants.Db.ZERO_COUNT
                : definition.events().size();
        long actions = definition == null
                ? Constants.Db.ZERO_COUNT
                : definition.actions().size();
        return new ProductItem(
                product.tenantId().toString(),
                product.productId(),
                product.name(),
                product.model(),
                product.categoryId(),
                latest == null ? null : latest.version(),
                latest == null ? null : latest.status(),
                properties,
                events,
                actions,
                binding == null || binding.profileId() == null ? null : binding.profileId().toString(),
                binding == null || binding.assetId() == null ? null : binding.assetId().toString(),
                binding == null || binding.ruleChainId() == null ? null : binding.ruleChainId().toString(),
                product.updatedAt());
    }

    private CatalogView catalog(TslDefinition definition, String version) {
        List<CatalogView.PropertyView> properties = definition.properties().stream()
                .map(this::propertyView)
                .toList();
        List<CatalogView.EventView> events = definition.events().stream()
                .map(this::eventView)
                .toList();
        List<CatalogView.ActionView> actions = definition.actions().stream()
                .map(this::actionView)
                .toList();
        return new CatalogView(definition.productId(), version, properties, events, actions);
    }

    private CatalogView.PropertyView propertyView(TslProperty property) {
        return new CatalogView.PropertyView(
                property.id(),
                property.name(),
                property.define() == null ? null : property.define().type(),
                property.mode(),
                property.define() == null ? null : property.define().unit(),
                property.define() == null ? null : property.define().min(),
                property.define() == null ? null : property.define().max(),
                property.define() == null ? null : property.define().step(),
                property.required(),
                property.mapping());
    }

    private CatalogView.EventView eventView(TslEvent event) {
        return new CatalogView.EventView(
                event.id(),
                event.name(),
                event.type(),
                objectMapper.valueToTree(event.params()));
    }

    private CatalogView.ActionView actionView(TslAction action) {
        return new CatalogView.ActionView(
                action.id(),
                action.name(),
                objectMapper.valueToTree(action.input()),
                objectMapper.valueToTree(action.output()));
    }

    private String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first;
        }
        if (second != null && !second.isBlank()) {
            return second;
        }
        return null;
    }
}

