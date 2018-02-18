/*
 * Copyright (c) 2017, 2018 RockNSM.
 *
 * This file is part of RockNSM
 * (see http://rocknsm.io).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */
import React, { Component } from 'react';
import { Col, Form, FormGroup, Input, Label, Collapse, Button, Card, CardHeader, CardBody, TabPane, TabContent, NavItem, NavLink, Nav } from 'reactstrap';
import classnames from 'classnames';

import 'react-widgets/dist/css/react-widgets.css';

import Moment from 'moment';
import momentLocalizer from 'react-widgets-moment';
import { DateTimePicker } from 'react-widgets';

Moment.locale('en');
momentLocalizer();

class Query extends Component {
/*
sensor[]
host[]
net[]
port[]
proto
proto-name (TCP, UDP, or ICMP)
before (RFC3339 string)
after (RFC3339 string)
before-ago (time in hrs or min)
after-ago (time in hrs or min)
limit packets (int)
limit bytes (int)
ignore weight (bool)

*/
  constructor(props) {
    super(props);

    var Config = require('Config');

    this.state = {
      advanced: false,
      activeHostNet: '1',
      activeDatetime: '1',
      apiURL: Config.serverUrl,
    };

    // Binds
    this.toggleAdvanced = this.toggleAdvanced.bind(this);
    this.toggleTabHostNet = this.toggleTabHostNet.bind(this);
    this.toggleTabDatetime = this.toggleTabDatetime.bind(this);
  }

  toggleTabHostNet(tab) {
    if ( this.state.activeHostNet !== tab ) {
      this.setState({ activeHostNet: tab });
    }
  }

  toggleTabDatetime(tab) {
    if ( this.state.activeDatetime !== tab ) {
      this.setState({ activeDatetime: tab });
    }
  }

  toggleAdvanced() {
    this.setState({ advanced: !this.state.advanced });
  }

  render() {
    return (
      <div className="animated fadeIn">
        <Card>
        <CardBody>
        <Form action={ this.state.apiURL } method="post" encType="multipart/form-data" className="form-horizontal">
          <div style={{ padding: '.5rem' }}>
          <Nav tabs>
          <NavItem>
            <NavLink
              className={classnames({active: this.state.activeDatetime === '1'})}
              onClick={() => this.toggleTabDatetime('1') }
            >
            Absolute Time
            </NavLink>
          </NavItem>
          <NavItem>
          <NavLink
            className={classnames({active: this.state.activeDatetime === '2'})}
            onClick={() => this.toggleTabDatetime('2') }
          >
          Relative Time
          </NavLink>
        </NavItem>
        </Nav>
        <TabContent activeTab={this.state.activeDatetime}>
        <TabPane tabId="1">
        <FormGroup row>
          <Label for="before" sm={2}>Before Date/Time</Label>
          <Col sm={6}>
          <DateTimePicker name="before" id="before" />
          </Col>
        </FormGroup>
        <FormGroup row>
          <Label for="after" sm={2}>After Date/Time</Label>
          <Col sm={6}>
          <DateTimePicker name="after" id="after" />
          </Col>
        </FormGroup>
        </TabPane>
        <TabPane tabId="2">
        <FormGroup row>
          <Label for="beforeAgo" sm={2}>Before</Label>
          <Col sm={3}>
          <Input type="number" step="1"/>
          </Col>
          <Col sm={3}>
          <Input type="select">
            <option value='m'>Minutes</option>
            <option value='h'>Hours</option>
          </Input>
          </Col>
          <Input type="text" name="before-ago" hidden />
        </FormGroup>
        <FormGroup row>
          <Label for="afterAgo" sm={2}>After</Label>
          <Col sm={3}>
          <Input type="number" step="1" id="afterAgo" />
          </Col>
          <Col sm={3}>
          <Input type="select">
            <option value='m'>Minutes</option>
            <option value='h'>Hours</option>
          </Input>
          </Col>
          <Input type="text" name="after-ago" hidden />
        </FormGroup>
        </TabPane>
        </TabContent>
        </div>

          <div style={{ padding: '.5rem' }}>
          <Nav tabs>
          <NavItem>
            <NavLink
              className={classnames({active: this.state.activeHostNet === '1'})}
              onClick={() => this.toggleTabHostNet('1') }
            >
            Host Query
            </NavLink>
          </NavItem>
          <NavItem>
          <NavLink
            className={classnames({active: this.state.activeHostNet === '2'})}
            onClick={() => this.toggleTabHostNet('2') }
          >
          Network Query
          </NavLink>
        </NavItem>
        </Nav>
        <TabContent activeTab={this.state.activeHostNet}>
        <TabPane tabId="1">
          <FormGroup row>
            <Label for="host1" sm={2}>First Host</Label>
            <Col sm={6}>
            <Input type="text" name="host" id="host1" placeholder="IP (e.g 192.168.100.1)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="host2" sm={2}>Second Host</Label>
            <Col sm={6}>
            <Input type="text" name="host" id="host2" placeholder="IP (e.g 192.168.100.1)" />
            </Col>
          </FormGroup>
        </TabPane>
        <TabPane tabId="2">
          <FormGroup row>
            <Label for="net1" sm={2}>First Net</Label>
            <Col sm={6}>
            <Input type="text" name="net" id="net1" placeholder="Network (e.g. 192.168.100.0/24)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="net2" sm={2}>Second Net</Label>
            <Col sm={6}>
            <Input type="text" name="net" id="net2" placeholder="Network (e.g. 192.168.100.0/24)" />
            </Col>
          </FormGroup>
        </TabPane>
        </TabContent>
        </div>

        <div style={{ padding: '.5rem' }}>
          <FormGroup row>
            <Label for="port1" sm={2}>First Port</Label>
            <Col sm={6}>
            <Input type="number" id="port1" name="port" placeholder="Port number (e.g. 1-65535)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="port2" sm={2}>Second Port</Label>
            <Col sm={6}>
            <Input type="number" id="port2" name="port" placeholder="Port number (e.g. 1-65535)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="protoName" sm={2}>Protocol</Label>
            <Col sm={6}>
            <Input type="select" name="proto-name" id="protoName">
              <option value=''></option>
              <option value='TCP'>TCP</option>
              <option value='UDP'>UDP</option>
              <option value='ICMP'>ICMP</option>
            </Input>
            </Col>
          </FormGroup>
        </div>


          <div style={{ padding: '.5rem' }}>
          <Button color="primary" onClick={this.toggleAdvanced} style={{ marginBottom: '1rem' }}>Advanced Settings</Button>
          <Collapse isOpen={this.state.advanced}>
          <FormGroup row>
            <Label for="limitPackets" sm={2}>Limit Packets</Label>
            <Col sm={6}>
            <Input type="number" id="limitPackets" name="steno-limit-packets" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="limitBytes" sm={2}>Limit Bytes</Label>
            <Col sm={6}>
            <Input type="number" id="limitBytes" name="steno-limit-bytes" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="protoNum" sm={2}>Protocol Number</Label>
            <Col sm={6}>
            <Input type="number" id="protoNum" name="proto" placeholder="IP Protocol Number (e.g. 0-255)"/>
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="ignoreWeight" sm={2}>Ignore Query Weight</Label>
            <Col sm={6}>
            <FormGroup check>
              <Label check>
              <Input type="checkbox" id="ignoreWeight" name="ignore-weight" />
              </Label>
            </FormGroup>
            </Col>
          </FormGroup>
          </Collapse>
          </div>
          </Form>
          </CardBody>
        </Card>
      </div>
    )
  }
}

export default Query;
