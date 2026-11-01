package com.iot.thingmodel.controller;

import com.iot.thingmodel.admin.TenantAccountRequest;
import com.iot.thingmodel.admin.TenantAccountService;
import com.iot.thingmodel.admin.TenantProvisionRequest;
import com.iot.thingmodel.admin.TenantProvisioningService;
import com.iot.thingmodel.auth.RequireAuthority;
import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.tb.ThingsboardClientProvider;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(Constants.Api.ADMIN_PATH)
@RequireAuthority(Constants.Auth.ROLE_SYS_ADMIN)
@Tag(name = "Admin", description = "Platform administration")
public class AdminController extends BaseController {

    private final TenantAccountService accountService;
    private final TenantProvisioningService provisioningService;
    private final ThingsboardClientProvider clientProvider;

    public AdminController(
            TenantAccountService accountService,
            TenantProvisioningService provisioningService,
            ThingsboardClientProvider clientProvider) {
        this.accountService = accountService;
        this.provisioningService = provisioningService;
        this.clientProvider = clientProvider;
    }

    @Operation(summary = "Register or update a vendor ThingsBoard account",
            description = "Stores an encrypted ThingsBoard tenant administrator account used by the platform.")
    @PostMapping("/tenants/{tenantId}/account")
    public TenantAccountService.MaskedAccount registerTenantAccount(
            @PathVariable String tenantId,
            @Valid @RequestBody TenantAccountRequest request) {
        UUID id = parseTenantId(tenantId);
        TenantAccountService.MaskedAccount saved = accountService.register(id, request.username(), request.password());
        clientProvider.evict(id);
        return saved;
    }

    @Operation(summary = "Provision a vendor ThingsBoard account",
            description = "Idempotently registers a vendor account or returns the existing one.")
    @PostMapping("/tenants/{tenantId}/provision")
    public TenantAccountService.MaskedAccount provisionTenantAccount(
            @PathVariable String tenantId,
            @Valid @RequestBody TenantProvisionRequest request) {
        UUID id = parseTenantId(tenantId);
        TenantAccountService.MaskedAccount saved = accountService.provision(
                id, request.username(), request.password(), request.force());
        clientProvider.evict(id);
        return saved;
    }

    @Operation(summary = "Automatically provision a vendor ThingsBoard account",
            description = "Creates a dedicated tenant admin service account and registers it.")
    @PostMapping("/tenants/{tenantId}/provision-auto")
    public TenantAccountService.MaskedAccount provisionTenantAccountAutomatically(
            @PathVariable String tenantId,
            @RequestParam(required = false, defaultValue = "false") boolean force,
            HttpServletRequest request) {
        UUID id = parseTenantId(tenantId);
        String token = (String) request.getAttribute(Constants.Auth.CURRENT_TOKEN_ATTRIBUTE);
        TenantAccountService.MaskedAccount saved =
                provisioningService.provisionAuto(id, token, force);
        clientProvider.evict(id);
        return saved;
    }

    @Operation(summary = "Get a vendor ThingsBoard account",
            description = "Returns the masked account information. The password is never returned.")
    @GetMapping("/tenants/{tenantId}/account")
    public TenantAccountService.MaskedAccount getTenantAccount(@PathVariable String tenantId) {
        UUID id = parseTenantId(tenantId);
        return checkNotNull(accountService.findMasked(id).orElse(null), "厂商租户未配置服务账号");
    }
}
