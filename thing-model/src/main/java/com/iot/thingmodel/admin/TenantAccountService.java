package com.iot.thingmodel.admin;

import com.iot.thingmodel.common.ApiException;
import com.iot.thingmodel.common.Constants;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class TenantAccountService {

    private static final Logger log = LoggerFactory.getLogger(TenantAccountService.class);

    private final TenantAccountRepository repository;
    private final CredentialCipher cipher;

    public TenantAccountService(TenantAccountRepository repository, CredentialCipher cipher) {
        this.repository = repository;
        this.cipher = cipher;
    }

    public MaskedAccount register(UUID tenantId, String username, String password) {
        if (tenantId == null) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST, Constants.ErrorCode.TENANT_ID_REQUIRED, "缺少租户 ID");
        }
        if (username == null || username.isBlank()) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST,
                    Constants.ErrorCode.USERNAME_REQUIRED,
                    "缺少服务账号用户名");
        }
        if (password == null || password.isBlank()) {
            throw new ApiException(
                    HttpStatus.BAD_REQUEST,
                    Constants.ErrorCode.PASSWORD_REQUIRED,
                    "缺少服务账号密码");
        }
        String normalizedUsername = username.trim();
        repository.upsert(tenantId, normalizedUsername, cipher.encrypt(password));
        return new MaskedAccount(tenantId, normalizedUsername, true);
    }

    public boolean isConfigured(UUID tenantId) {
        return repository.find(tenantId).map(TenantAccountRepository.TenantAccountRow::enabled).orElse(false);
    }

    public void requireConfigured(UUID tenantId) {
        credentials(tenantId);
    }

    public MaskedAccount provision(UUID tenantId, String username, String password, boolean force) {
        return findMasked(tenantId)
                .filter(account -> !force)
                .orElseGet(() -> register(tenantId, username, password));
    }

    public TenantCredentials credentials(UUID tenantId) {
        TenantAccountRepository.TenantAccountRow row = repository.find(tenantId)
                .orElseThrow(() -> new ApiException(
                        HttpStatus.BAD_REQUEST,
                        Constants.ErrorCode.TENANT_ACCOUNT_MISSING,
                        "厂商租户 " + tenantId + " 未配置 ThingsBoard 服务账号"));
        if (!row.enabled()) {
            throw new ApiException(
                    HttpStatus.FORBIDDEN,
                    Constants.ErrorCode.TENANT_ACCOUNT_DISABLED,
                    "厂商租户服务账号已停用");
        }
        String password;
        try {
            password = cipher.decrypt(row.passwordCipher());
        } catch (IllegalStateException ex) {
            log.warn("Tenant {} service account credentials cannot be decrypted: {}",
                    tenantId, ex.getMessage());
            throw new ApiException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    Constants.ErrorCode.TENANT_CREDENTIAL_DECRYPT_FAILED,
                    "厂商租户服务账号凭据无法解密，可能是 THINGMODEL_SECRET_KEY 已变更。"
                            + "请重新执行 provision-auto 或重新注册服务账号");
        }
        return new TenantCredentials(row.username(), password);
    }

    public Optional<MaskedAccount> findMasked(UUID tenantId) {
        return repository.find(tenantId).map(row -> new MaskedAccount(row.tenantId(), row.username(), row.enabled()));
    }

    public record MaskedAccount(UUID tenantId, String username, boolean enabled) {
    }

    public static final class TenantCredentials {

        private final String username;
        private final String password;

        public TenantCredentials(String username, String password) {
            this.username = username;
            this.password = password;
        }

        public String username() {
            return username;
        }

        public String password() {
            return password;
        }

        @Override
        public String toString() {
            return "TenantCredentials{username='" + username
                    + "', password='" + Constants.Auth.MASKED_PASSWORD + "'}";
        }
    }
}
