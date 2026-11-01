package com.iot.thingmodel.admin;

import com.iot.thingmodel.common.ApiException;
import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.config.ThingModelProperties;
import com.iot.thingmodel.tb.ThingsboardAdminClientProvider;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.thingsboard.client.ThingsboardClient;
import org.thingsboard.client.api.ThingsboardApi;
import org.thingsboard.client.model.ActivateUserRequest;
import org.thingsboard.client.model.Authority;
import org.thingsboard.client.model.PageDataUser;
import org.thingsboard.client.model.TenantId;
import org.thingsboard.client.model.User;

@Service
public class TenantProvisioningService {

    private static final Pattern ACTIVATE_TOKEN_PATTERN =
            Pattern.compile("[?&]activateToken=([^&]+)");
    private static final char[] UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ".toCharArray();
    private static final char[] LOWER = "abcdefghijkmnopqrstuvwxyz".toCharArray();
    private static final char[] DIGITS = "23456789".toCharArray();
    private static final char[] SPECIAL = "!@#$%^&*".toCharArray();
    private static final int PASSWORD_LENGTH = 24;
    private static final int PAGE_SIZE = 100;
    private static final int MAX_PAGES = 10;

    private final TenantAccountService accountService;
    private final ThingsboardAdminClientProvider adminClientProvider;
    private final ThingModelProperties properties;
    private final SecureRandom random = new SecureRandom();

    public TenantProvisioningService(
            TenantAccountService accountService,
            ThingsboardAdminClientProvider adminClientProvider,
            ThingModelProperties properties) {
        this.accountService = accountService;
        this.adminClientProvider = adminClientProvider;
        this.properties = properties;
    }

    public TenantAccountService.MaskedAccount provisionAuto(
            UUID tenantId, String sysadminToken, boolean force) {
        if (tenantId == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TENANT_ID_REQUIRED, "缺少租户 ID");
        }
        if (sysadminToken == null || sysadminToken.isBlank()) {
            throw new ApiException(
                    HttpStatus.UNAUTHORIZED, Constants.ErrorCode.UNAUTHORIZED, "缺少访问令牌");
        }

        ThingsboardClient client = adminClientProvider.get(sysadminToken);
        requireTenant(client, tenantId);

        Optional<TenantAccountService.MaskedAccount> existing = accountService.findMasked(tenantId);
        if (existing.isPresent() && !force) {
            return existing.get();
        }

        String email = serviceAccountEmail(tenantId);
        User existingUser = findTenantAdminByEmail(client, tenantId, email);
        if (existingUser != null) {
            if (!force) {
                throw new ApiException(
                        HttpStatus.CONFLICT,
                        Constants.ErrorCode.TENANT_ACCOUNT_CONFLICT,
                        "租户服务账号用户已存在但账号表缺失，请使用 force=true 重建");
            }
            deleteUser(client, existingUser.getId().getId().toString());
        }

        String password = generatePassword();
        User user = new User()
                .tenantId(new TenantId().id(tenantId))
                .email(email)
                .authority(Authority.TENANT_ADMIN)
                .firstName("thing-model")
                .lastName("service");

        User savedUser;
        try {
            savedUser = client.saveUser(ThingsboardApi.SaveUserArgs.builder()
                    .user(user)
                    .sendActivationMail("false")
                    .build());
        } catch (org.thingsboard.client.ApiException ex) {
            throw adminFailure("创建租户管理员失败", ex);
        }

        try {
            String activationLink = client.getActivationLink(savedUser.getId().getId().toString());
            String activateToken = extractActivateToken(activationLink);
            ActivateUserRequest activateRequest = new ActivateUserRequest()
                    .activateToken(activateToken)
                    .password(password);
            client.activateUser(activateRequest, false);
            return accountService.register(tenantId, email, password);
        } catch (Exception ex) {
            deleteUser(client, savedUser.getId().getId().toString());
            if (ex instanceof ApiException apiException) {
                throw apiException;
            }
            if (ex instanceof org.thingsboard.client.ApiException apiException) {
                throw adminFailure("激活租户管理员失败", apiException);
            }
            throw new ApiException(
                    HttpStatus.BAD_GATEWAY,
                    Constants.ErrorCode.TB_UNAVAILABLE,
                    "自动初始化厂商服务账号失败: " + ex.getMessage());
        }
    }

    private void requireTenant(ThingsboardClient client, UUID tenantId) {
        try {
            client.getTenantById(tenantId.toString());
        } catch (org.thingsboard.client.ApiException ex) {
            if (ex.getCode() == HttpStatus.NOT_FOUND.value()) {
                throw new ApiException(
                        HttpStatus.NOT_FOUND,
                        Constants.ErrorCode.TENANT_NOT_FOUND,
                        "ThingsBoard 租户不存在: " + tenantId);
            }
            throw adminFailure("查询 ThingsBoard 租户失败", ex);
        }
    }

    private User findTenantAdminByEmail(ThingsboardClient client, UUID tenantId, String email) {
        try {
            for (int page = 0; page < MAX_PAGES; page++) {
                PageDataUser users = client.getTenantAdmins(
                        tenantId.toString(), PAGE_SIZE, page, null, null, null);
                if (users == null || users.getData() == null) {
                    return null;
                }
                for (User user : users.getData()) {
                    if (email.equalsIgnoreCase(user.getEmail())) {
                        return user;
                    }
                }
                if (!Boolean.TRUE.equals(users.getHasNext())) {
                    return null;
                }
            }
            return null;
        } catch (org.thingsboard.client.ApiException ex) {
            throw adminFailure("查询租户管理员失败", ex);
        }
    }

    private void deleteUser(ThingsboardClient client, String userId) {
        try {
            client.deleteUser(userId);
        } catch (org.thingsboard.client.ApiException ignored) {
            // Best-effort compensation; keep the original failure instead.
        }
    }

    private String serviceAccountEmail(UUID tenantId) {
        String domain = properties.getAdmin().getServiceAccountEmailDomain();
        if (domain == null || domain.isBlank()) {
            domain = Constants.Defaults.SERVICE_ACCOUNT_EMAIL_DOMAIN;
        }
        return "thing-model-svc-" + tenantId + "@" + domain.trim();
    }

    private String extractActivateToken(String activationLink) {
        if (activationLink == null || activationLink.isBlank()) {
            throw new IllegalStateException("ThingsBoard 未返回激活链接");
        }
        Matcher matcher = ACTIVATE_TOKEN_PATTERN.matcher(activationLink);
        if (!matcher.find()) {
            throw new IllegalStateException("无法从激活链接解析 activateToken");
        }
        return URLDecoder.decode(matcher.group(1), StandardCharsets.UTF_8);
    }

    private String generatePassword() {
        char[] password = new char[PASSWORD_LENGTH];
        password[0] = UPPER[random.nextInt(UPPER.length)];
        password[1] = LOWER[random.nextInt(LOWER.length)];
        password[2] = DIGITS[random.nextInt(DIGITS.length)];
        password[3] = SPECIAL[random.nextInt(SPECIAL.length)];
        String all = new String(UPPER) + new String(LOWER) + new String(DIGITS) + new String(SPECIAL);
        for (int i = 4; i < password.length; i++) {
            password[i] = all.charAt(random.nextInt(all.length()));
        }
        for (int i = password.length - 1; i > 0; i--) {
            int j = random.nextInt(i + 1);
            char tmp = password[i];
            password[i] = password[j];
            password[j] = tmp;
        }
        return new String(password);
    }

    private ApiException adminFailure(String action, org.thingsboard.client.ApiException ex) {
        if (ex.getCode() == HttpStatus.CONFLICT.value()) {
            return new ApiException(
                    HttpStatus.CONFLICT,
                    Constants.ErrorCode.TENANT_ACCOUNT_CONFLICT,
                    action + ": 服务账号用户已存在");
        }
        return new ApiException(
                HttpStatus.BAD_GATEWAY,
                Constants.ErrorCode.TB_UNAVAILABLE,
                action + ": HTTP " + ex.getCode());
    }
}
