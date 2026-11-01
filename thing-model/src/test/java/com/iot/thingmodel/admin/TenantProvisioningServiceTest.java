package com.iot.thingmodel.admin;

import com.iot.thingmodel.common.ApiException;
import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.config.ThingModelProperties;
import com.iot.thingmodel.tb.ThingsboardAdminClientProvider;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.thingsboard.client.ThingsboardClient;
import org.thingsboard.client.api.ThingsboardApi;
import org.thingsboard.client.model.ActivateUserRequest;
import org.thingsboard.client.model.PageDataUser;
import org.thingsboard.client.model.Tenant;
import org.thingsboard.client.model.User;
import org.thingsboard.client.model.UserId;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TenantProvisioningServiceTest {

    private final UUID tenantId = UUID.randomUUID();
    private final UUID userId = UUID.randomUUID();
    private final ThingsboardClient client = mock(ThingsboardClient.class);
    private final ThingsboardAdminClientProvider clientProvider =
            mock(ThingsboardAdminClientProvider.class);
    private final TenantAccountService accountService = mock(TenantAccountService.class);
    private final ThingModelProperties properties = new ThingModelProperties();
    private final TenantProvisioningService service =
            new TenantProvisioningService(accountService, clientProvider, properties);
    private final String email = "thing-model-svc-" + tenantId + "@thing-model.local";

    @BeforeEach
    void setUp() {
        when(clientProvider.get("token")).thenReturn(client);
    }

    @Test
    void createsAndActivatesDedicatedTenantAdmin() throws Exception {
        when(client.getTenantById(tenantId.toString())).thenReturn(new Tenant());
        when(accountService.findMasked(tenantId)).thenReturn(Optional.empty());
        when(client.getTenantAdmins(
                eq(tenantId.toString()), eq(100), eq(0), isNull(), isNull(), isNull()))
                .thenReturn(emptyUsers());
        when(client.saveUser(any(ThingsboardApi.SaveUserArgs.class))).thenAnswer(invocation -> {
            User user = new User();
            user.setId(new UserId().id(userId));
            user.setEmail(email);
            return user;
        });
        when(client.getActivationLink(userId.toString()))
                .thenReturn("http://localhost:18080/api/noauth/activate?activateToken=abc");
        when(accountService.register(eq(tenantId), eq(email), anyString()))
                .thenReturn(new TenantAccountService.MaskedAccount(tenantId, email, true));

        TenantAccountService.MaskedAccount account =
                service.provisionAuto(tenantId, "token", false);

        assertEquals(email, account.username());
        verify(client).activateUser(any(ActivateUserRequest.class), eq(false));
        verify(accountService).register(eq(tenantId), eq(email), anyString());
    }

    @Test
    void returnsExistingAccountWithoutCreatingUser() throws Exception {
        when(client.getTenantById(tenantId.toString())).thenReturn(new Tenant());
        when(accountService.findMasked(tenantId)).thenReturn(Optional.of(
                new TenantAccountService.MaskedAccount(tenantId, email, true)));

        TenantAccountService.MaskedAccount account =
                service.provisionAuto(tenantId, "token", false);

        assertEquals(email, account.username());
        verify(client, never()).saveUser(any(ThingsboardApi.SaveUserArgs.class));
        verify(accountService, never()).register(any(), anyString(), anyString());
    }

    @Test
    void rejectsMissingTenant() throws Exception {
        when(client.getTenantById(tenantId.toString()))
                .thenThrow(new org.thingsboard.client.ApiException(404, "not found"));

        ApiException ex = assertThrows(ApiException.class,
                () -> service.provisionAuto(tenantId, "token", false));

        assertEquals(HttpStatus.NOT_FOUND.value(), ex.getStatus().value());
        assertEquals(Constants.ErrorCode.TENANT_NOT_FOUND, ex.getCode());
    }

    private PageDataUser emptyUsers() {
        PageDataUser page = new PageDataUser();
        page.setData(List.of());
        return page;
    }
}
