package com.iot.thingmodel.sync;

import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.tb.TbSyncException;
import com.iot.thingmodel.tb.ThingsboardClientProvider;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.thingsboard.client.ThingsboardClient;
import org.thingsboard.client.model.Device;
import org.thingsboard.client.model.DeviceProfileId;
import org.thingsboard.client.model.PageDataDevice;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TbProductResourceDeleterTest {

    private final UUID tenantId = UUID.randomUUID();
    private final ThingsboardClientProvider provider = mock(ThingsboardClientProvider.class);
    private final ThingsboardClient client = mock(ThingsboardClient.class);
    private final TbProductResourceDeleter deleter = new TbProductResourceDeleter(provider);

    @Test
    void countsDevicesMatchingProfile() throws Exception {
        UUID profileId = UUID.randomUUID();
        Device device = new Device();
        device.setDeviceProfileId(new DeviceProfileId().id(profileId));
        PageDataDevice page = new PageDataDevice(1, 1L, false);
        page.setData(List.of(device));
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getTenantDevices(
                Constants.ThingsBoard.PAGE_SIZE,
                Constants.ThingsBoard.FIRST_PAGE,
                null,
                null,
                Constants.ThingsBoard.SORT_PROPERTY_NAME,
                Constants.ThingsBoard.SORT_ORDER_ASC))
                .thenReturn(page);

        long count = deleter.countDevices(tenantId, Set.of(profileId));

        assertEquals(1L, count);
    }

    @Test
    void ignoresDevicesFromOtherProfiles() throws Exception {
        UUID profileId = UUID.randomUUID();
        Device device = new Device();
        device.setDeviceProfileId(new DeviceProfileId().id(UUID.randomUUID()));
        PageDataDevice page = new PageDataDevice(1, 1L, false);
        page.setData(List.of(device));
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getTenantDevices(
                eq(Constants.ThingsBoard.PAGE_SIZE),
                eq(Constants.ThingsBoard.FIRST_PAGE),
                isNull(),
                isNull(),
                eq(Constants.ThingsBoard.SORT_PROPERTY_NAME),
                eq(Constants.ThingsBoard.SORT_ORDER_ASC)))
                .thenReturn(page);

        assertEquals(0L, deleter.countDevices(tenantId, Set.of(profileId)));
    }

    @Test
    void deletesProfilesRuleChainsAndAssets() throws Exception {
        UUID profileId = UUID.randomUUID();
        UUID assetId = UUID.randomUUID();
        UUID ruleChainId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);

        deleter.deleteResources(
                tenantId, Set.of(profileId), Set.of(assetId), Set.of(ruleChainId));

        verify(client).deleteDeviceProfile(profileId.toString());
        verify(client).deleteRuleChain(ruleChainId.toString());
        verify(client).deleteAsset(assetId.toString());
    }

    @Test
    void ignoresMissingResources() throws Exception {
        UUID profileId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        doThrow(new org.thingsboard.client.ApiException(404, "not found"))
                .when(client).deleteDeviceProfile(profileId.toString());

        assertDoesNotThrow(() -> deleter.deleteResources(
                tenantId, Set.of(profileId), Set.of(), Set.of()));
    }

    @Test
    void translatesOtherDeleteFailures() throws Exception {
        UUID assetId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        doThrow(new org.thingsboard.client.ApiException(500, "boom"))
                .when(client).deleteAsset(assetId.toString());

        assertThrows(TbSyncException.class, () -> deleter.deleteResources(
                tenantId, Set.of(), Set.of(assetId), Set.of()));
    }
}
