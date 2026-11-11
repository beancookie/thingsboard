package com.iot.thingmodel.admin;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TenantCredentialStartupValidatorTest {

    private final TenantAccountRepository repository = mock(TenantAccountRepository.class);
    private final CredentialCipher cipher = mock(CredentialCipher.class);
    private final TenantCredentialStartupValidator validator =
            new TenantCredentialStartupValidator(repository, cipher);

    @Test
    void warnsWithoutFailingWhenCredentialCannotBeDecrypted() {
        UUID tenantId = UUID.randomUUID();
        TenantAccountRepository.TenantAccountRow row = new TenantAccountRepository.TenantAccountRow(
                tenantId, "user", "cipher", true, Instant.now(), Instant.now());
        when(repository.listEnabled()).thenReturn(List.of(row));
        when(cipher.decrypt("cipher")).thenThrow(new IllegalStateException("Tag mismatch"));

        assertDoesNotThrow(validator::validateStoredCredentials);

        verify(cipher).decrypt("cipher");
    }
}
