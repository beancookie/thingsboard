package com.iot.thingmodel.sync;

import com.iot.thingmodel.common.Constants;
import com.iot.thingmodel.tb.TbExceptionTranslator;
import com.iot.thingmodel.tb.TbSyncException;
import com.iot.thingmodel.tb.ThingsboardClientProvider;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Component;
import org.thingsboard.client.ThingsboardClient;
import org.thingsboard.client.model.PageDataDevice;

@Component
public class TbProductResourceDeleter {

    private static final int COUNT_PAGE_SIZE = 1;

    private final ThingsboardClientProvider clientProvider;

    public TbProductResourceDeleter(ThingsboardClientProvider clientProvider) {
        this.clientProvider = clientProvider;
    }

    public long countDevices(UUID tenantId, Set<UUID> profileIds) {
        if (isEmpty(profileIds)) {
            return Constants.Db.ZERO_COUNT;
        }
        ThingsboardClient client = clientProvider.get(tenantId);
        long count = Constants.Db.ZERO_COUNT;
        for (UUID profileId : profileIds) {
            try {
                String profileName = client
                        .getDeviceProfileById(profileId.toString(), false)
                        .getName();
                PageDataDevice result = client.getTenantDevices(
                        COUNT_PAGE_SIZE,
                        Constants.ThingsBoard.FIRST_PAGE,
                        profileName,
                        null,
                        Constants.ThingsBoard.SORT_PROPERTY_NAME,
                        Constants.ThingsBoard.SORT_ORDER_ASC);
                if (result != null && result.getTotalElements() != null) {
                    count += result.getTotalElements();
                }
            } catch (org.thingsboard.client.ApiException ex) {
                if (ex.getCode() == 404) {
                    continue;
                }
                throw TbExceptionTranslator.translate("检查产品设备", ex);
            }
        }
        return count;
    }

    public void deleteResources(
            UUID tenantId,
            Set<UUID> profileIds,
            Set<UUID> assetIds,
            Set<UUID> ruleChainIds) {
        if (isEmpty(profileIds) && isEmpty(assetIds) && isEmpty(ruleChainIds)) {
            return;
        }
        ThingsboardClient client = clientProvider.get(tenantId);
        if (profileIds != null) {
            profileIds.forEach(id -> delete(
                    "删除设备模板", () -> client.deleteDeviceProfile(id.toString())));
        }
        if (ruleChainIds != null) {
            ruleChainIds.forEach(id -> delete(
                    "删除规则链", () -> client.deleteRuleChain(id.toString())));
        }
        if (assetIds != null) {
            assetIds.forEach(id -> delete(
                    "删除产品资产", () -> client.deleteAsset(id.toString())));
        }
    }

    private void delete(String action, TbDeleteAction deleteAction) {
        try {
            deleteAction.run();
        } catch (org.thingsboard.client.ApiException ex) {
            if (ex.getCode() == 404) {
                return;
            }
            throw TbExceptionTranslator.translate(action, ex);
        }
    }

    private boolean isEmpty(Set<UUID> values) {
        return values == null || values.isEmpty();
    }

    @FunctionalInterface
    private interface TbDeleteAction {
        void run() throws org.thingsboard.client.ApiException;
    }
}
