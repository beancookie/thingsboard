package com.iot.thingmodel.sync;

import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.tb.TbSyncException;
import com.iot.thingmodel.tb.ThingsboardClientProvider;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.thingsboard.client.ThingsboardClient;
import org.thingsboard.client.model.DeviceProfile;
import org.thingsboard.client.model.PageDataDevice;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
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
    void countsDevicesByDeviceProfile() throws Exception {
        UUID profileId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getDeviceProfileById(profileId.toString(), false))
                .thenReturn(deviceProfile("helmet"));
        when(client.getTenantDevices(
                1,
                Constants.ThingsBoard.FIRST_PAGE,
                "helmet",
                null,
                Constants.ThingsBoard.SORT_PROPERTY_NAME,
                Constants.ThingsBoard.SORT_ORDER_ASC))
                .thenReturn(new PageDataDevice(1, 1L, false));

        long count = deleter.countDevices(tenantId, Set.of(profileId));

        assertEquals(1L, count);
    }

    @Test
    void sumsDeviceCountsAcrossProfiles() throws Exception {
        UUID profileA = UUID.randomUUID();
        UUID profileB = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getDeviceProfileById(profileA.toString(), false))
                .thenReturn(deviceProfile("helmet-a"));
        when(client.getDeviceProfileById(profileB.toString(), false))
                .thenReturn(deviceProfile("helmet-b"));
        when(client.getTenantDevices(
                1,
                Constants.ThingsBoard.FIRST_PAGE,
                "helmet-a",
                null,
                Constants.ThingsBoard.SORT_PROPERTY_NAME,
                Constants.ThingsBoard.SORT_ORDER_ASC))
                .thenReturn(new PageDataDevice(1, 2L, false));
        when(client.getTenantDevices(
                1,
                Constants.ThingsBoard.FIRST_PAGE,
                "helmet-b",
                null,
                Constants.ThingsBoard.SORT_PROPERTY_NAME,
                Constants.ThingsBoard.SORT_ORDER_ASC))
                .thenReturn(new PageDataDevice(1, 3L, false));

        long count = deleter.countDevices(tenantId, Set.of(profileA, profileB));

        assertEquals(5L, count);
    }

    @Test
    void ignoresMissingDeviceProfile() throws Exception {
        UUID profileId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getDeviceProfileById(profileId.toString(), false))
                .thenThrow(new org.thingsboard.client.ApiException(404, "not found"));

        assertEquals(0L, deleter.countDevices(tenantId, Set.of(profileId)));
    }

    @Test
    void translatesCountFailures() throws Exception {
        UUID profileId = UUID.randomUUID();
        when(provider.get(tenantId)).thenReturn(client);
        when(client.getDeviceProfileById(profileId.toString(), false))
                .thenThrow(new org.thingsboard.client.ApiException(0, "io failure"));

        assertThrows(TbSyncException.class,
                () -> deleter.countDevices(tenantId, Set.of(profileId)));
    }

    private static DeviceProfile deviceProfile(String name) {
        DeviceProfile profile = new DeviceProfile();
        profile.setName(name);
        return profile;
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
