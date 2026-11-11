package com.iot.thingmodel.admin;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class TenantCredentialStartupValidator {

    private static final Logger log = LoggerFactory.getLogger(TenantCredentialStartupValidator.class);

    private final TenantAccountRepository repository;
    private final CredentialCipher cipher;

    public TenantCredentialStartupValidator(
            TenantAccountRepository repository, CredentialCipher cipher) {
        this.repository = repository;
        this.cipher = cipher;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void validateStoredCredentials() {
        for (TenantAccountRepository.TenantAccountRow row : repository.listEnabled()) {
            try {
                cipher.decrypt(row.passwordCipher());
            } catch (RuntimeException ex) {
                log.warn("Tenant {} service account credentials cannot be decrypted with the current "
                                + "THINGMODEL_SECRET_KEY. Re-provision the account before syncing products.",
                        row.tenantId());
            }
        }
    }
}
