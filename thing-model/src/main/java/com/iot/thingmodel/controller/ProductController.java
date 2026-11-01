package com.iot.thingmodel.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.iot.thingmodel.auth.AccessGuard;
import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.auth.CurrentUser;
import com.iot.thingmodel.auth.RequireAuthority;
import com.iot.thingmodel.product.CatalogView;
import com.iot.thingmodel.product.CreateProductCommand;
import com.iot.thingmodel.product.CreateProductRequest;
import com.iot.thingmodel.product.ProductDetail;
import com.iot.thingmodel.product.ProductItem;
import com.iot.thingmodel.product.ProductResponse;
import com.iot.thingmodel.product.ProductService;
import com.iot.thingmodel.product.ThingModelView;
import com.iot.thingmodel.product.UpdateThingModelRequest;
import com.iot.thingmodel.product.ValidationResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(Constants.Api.PRODUCTS_PATH)
@RequireAuthority({Constants.Auth.ROLE_TENANT_ADMIN, Constants.Auth.ROLE_SYS_ADMIN})
@Tag(name = "Products", description = "Product and thing model management")
public class ProductController extends BaseController {

    private final ProductService productService;

    public ProductController(AccessGuard accessGuard, ProductService productService) {
        super(accessGuard);
        this.productService = productService;
    }

    @Operation(summary = "List products")
    @GetMapping
    public List<ProductItem> list(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String tenantId) {
        CurrentUser currentUser = getCurrentUser();
        UUID filterTenant = accessGuard.resolveListTenant(currentUser, tenantId);
        return productService.list(tenantScope(), filterTenant, keyword);
    }

    @Operation(summary = "Get product details")
    @GetMapping("/{productId}")
    public ProductDetail get(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.get(resolvedTenant, productId);
    }

    @Operation(summary = "Get the latest thing model")
    @GetMapping("/{productId}/thing-model")
    public ThingModelView getThingModel(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.getThingModel(resolvedTenant, productId);
    }

    @Operation(summary = "Create or update a product and publish its thing model")
    @PostMapping
    public ProductResponse create(@Valid @RequestBody CreateProductRequest request) {
        CurrentUser currentUser = getCurrentUser();
        UUID tenantId = accessGuard.resolveWriteTenant(currentUser, request.tenantId());
        accessGuard.checkTenantAccess(currentUser, tenantId);
        return productService.create(new CreateProductCommand(
                tenantId,
                request.productId(),
                request.name(),
                request.model(),
                request.categoryId(),
                request.tslVersion(),
                request.tsl(),
                Boolean.TRUE.equals(request.strictUnknown())));
    }

    @Operation(summary = "Submit a new thing model version")
    @PutMapping("/{productId}/thing-model")
    public ProductResponse updateThingModel(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId,
            @Valid @RequestBody UpdateThingModelRequest request) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.updateThingModel(resolvedTenant, productId, request);
    }

    @Operation(summary = "Validate a thing model without persisting it")
    @PostMapping("/{productId}/thing-model/validate")
    public ValidationResponse validate(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId,
            @RequestBody JsonNode body) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.validate(resolvedTenant, productId, body);
    }

    @Operation(summary = "Get the thing model catalog")
    @GetMapping("/{productId}/catalog")
    public CatalogView catalog(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.catalog(resolvedTenant, productId);
    }

    @Operation(summary = "Re-sync the product with ThingsBoard")
    @PostMapping("/{productId}/sync")
    public ProductResponse sync(
            @PathVariable String productId,
            @RequestParam(required = false) String tenantId) {
        UUID resolvedTenant = accessGuard.resolveProductTenant(getCurrentUser(), tenantId);
        return productService.sync(resolvedTenant, productId);
    }
}
