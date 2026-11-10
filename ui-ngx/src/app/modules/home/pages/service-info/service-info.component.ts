// SPDX-FileCopyrightText: Copyright The Thingsboard Authors
// SPDX-License-Identifier: Apache-2.0
import { Component } from '@angular/core';

export interface ServiceEndpoint {
  key: string;
  protocol: string;
  transport: string;
  address: string;
}

@Component({
  selector: 'tb-service-info',
  templateUrl: './service-info.component.html',
  styleUrls: ['./service-info.component.scss'],
  standalone: false
})
export class ServiceInfoComponent {

  readonly deviceEndpoints: ServiceEndpoint[] = [
    {
      key: 'mqtt',
      protocol: 'MQTT',
      transport: 'TCP',
      address: '129.211.241.31:1883'
    },
    {
      key: 'coap',
      protocol: 'CoAP',
      transport: 'UDP',
      address: '129.211.239.15:5683'
    },
    {
      key: 'http',
      protocol: 'HTTP',
      transport: 'HTTP',
      address: '1.13.164.152:30808'
    }
  ];

  readonly apiEndpoints: ServiceEndpoint[] = [
    {
      key: 'rest-thingsboard',
      protocol: 'HTTPS',
      transport: 'REST',
      address: 'https://thingsboard.zhgcloud.com'
    },
    {
      key: 'rest-thingmodel',
      protocol: 'HTTPS',
      transport: 'REST',
      address: 'https://thingsboard.zhgcloud.com/api/thing-model'
    }
  ];
}
