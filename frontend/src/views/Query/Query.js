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
import { Col, Form, FormGroup, Input, Label, Collapse, Button, Card, CardHeader, CardBody, CardFooter, TabPane, TabContent, NavItem, NavLink, Nav } from 'reactstrap';
import classnames from 'classnames';

import 'react-widgets/dist/css/react-widgets.css';

import Moment from 'moment';
import momentLocalizer from 'react-widgets-moment';
import { DateTimePicker } from 'react-widgets';

Moment.locale('en');
momentLocalizer();

String.prototype.betterReplace = function(search, replace, from) {
  if (this.length > from) {
    return this.slice(0, from) + this.slice(from).replace(search, replace);
  }
  return this;
}

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
      data: {
        after: null,
        before: null,
        afterAgo: '',
        afterAgoUnit: 'm',
        beforeAgo: '',
        beforeAgoUnit: 'm',
        host1: '',
        host2: '',
        net1: '',
        net2: '',
        port1: '',
        port2: '',
        protoName: '',
        limitPackets: '',
        limitBytes: '',
        proto: '',
        ignoreWeight: false,
      },
    };

    // Binds
    this.toggleAdvanced = this.toggleAdvanced.bind(this);
    this.toggleTabHostNet = this.toggleTabHostNet.bind(this);
    this.toggleTabDatetime = this.toggleTabDatetime.bind(this);

    this.handleChange = this.handleChange.bind(this);
    this.handleDateTimeChange = this.handleDateTimeChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleReset = this.handleReset.bind(this);
  }

  handleReset(event) {
    const data = this.state.data;
    const defaults = {
      after: null,
      before: null,
      afterAgo: '',
      afterAgoUnit: 'm',
      beforeAgo: '',
      beforeAgoUnit: 'm',
      host1: '',
      host2: '',
      net1: '',
      net2: '',
      port1: '',
      port2: '',
      protoName: '',
      limitPackets: '',
      limitBytes: '',
      proto: '',
      ignoreWeight: false,
    };

    this.setState({
      data: defaults });

    console.log('internal state', this.state.data );
    event.preventDefault();

  }

  handleSubmit(event) {
    console.log('internal state data', this.state.data);
    event.preventDefault();

    var Config = require('Config');
    let data = this.state.data;

    // Absolute time query
    if (! data['after'])
      delete data['after'];
    if (! data['before'])
      delete data['before'];

    // Relative time query
    if (data['afterAgo']) {
      data['after-ago'] = data['afterAgo'] + data['afterAgoUnit'];
    }
    delete data['afterAgo'];
    delete data['afterAgoUnit'];

    if (data['beforeAgo']) {
      data['before-ago'] = data['beforeAgo'] + data['beforeAgoUnit'];
    }
    delete data['beforeAgo'];
    delete data['beforeAgoUnit'];

    // Process host entries
    data['host'] = [];
    if (data['host1'])
      data['host'].push(data['host1']);
    if (data['host2'])
      data['host'].push(data['host2']);
    if (data['host'].length === 0)
      delete data['host'];

    delete data['host1'];
    delete data['host2'];

    // Process net entries
    data['net'] = [];
    if (data['net1'])
      data['net'].push(data['net1']);
    if (data['net2'])
      data['net'].push(data['net2']);
    if (data['net'].length === 0)
      delete data['net'];

    delete data['net1'];
    delete data['net2'];

    // Process port entries
    data['port'] = [];
    if (data['port1'])
      data['port'].push(data['port1']);
    if (data['port2'])
      data['port'].push(data['port2']);
    if (data['port'].length === 0)
      delete data['port'];

    delete data['port1'];
    delete data['port2'];

    // Process protocol
    if (data['protoName'])
      data['proto-name'] = data['protoName'];
    delete data['protoName'];

    if (! data['proto'])
      delete data['proto'];

    if (data['limitPackets'])
      data['Steno-Limit-Packets'] = data['limitPackets'];
    delete data['limitPackets'];

    if (data['limitBytes'])
      data['Steno-Limit-Bytes'] = data['limitBytes'];
    delete data['limitBytes'];

    if (data['ignoreWeight'])
      data['ignore-weight'] = data['ignoreWeight'];
    delete data['ignoreWeight'];

    console.log('form post data', JSON.stringify(data));

    let formUrl = (window.location.origin +
                   window.location.pathname +
                   Config.serverUrl).betterReplace(
                     /\/\//g, '/', window.location.origin.indexOf('//')+2
                   );
    console.log('POST to ', formUrl );
    var result = fetch(formUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    }).then((response) => response.json())
      .then((responseJson) => {
        console.log("ResponseJson", responseJson);
        this.props.history.push('/status/' + responseJson.id);
      });

    // Need to scrub the empty data
  }

  handleDateTimeChange(field, value) {
    this.handleChange({target: {name: field, type: 'datetime', value: value}});
  }

  handleChange(event) {
    const target = event.target;

    const value = target.type === 'checkbox' ? target.checked : target.value;
    const name = target.name;
    const data = this.state.data;

    console.log(name, value)
    this.setState({
      data: Object.assign(data, { [name]: value })
    });
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
        <Form onSubmit={ this.handleSubmit } name="query_form" className="form-horizontal">
        <CardBody>
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
          <Label for="after" sm={2}>After Date/Time</Label>
          <Col sm={6}>
          <DateTimePicker name="after"
            value={ this.state.data.after }
            onChange={ this.handleDateTimeChange.bind(this, 'after') } />
          </Col>
        </FormGroup>
        <FormGroup row>
          <Label for="before" sm={2}>Before Date/Time</Label>
          <Col sm={6}>
          <DateTimePicker name="before"
            value={ this.state.data.before }
            onChange={ this.handleDateTimeChange.bind(this, 'before') } />
          </Col>
        </FormGroup>
        </TabPane>
        <TabPane tabId="2">

        <FormGroup row>
          <Label for="afterAgo" sm={2}>After</Label>
          <Col sm={3}>
          <Input type="number" name="afterAgo"
            value={ this.state.data.afterAgo }
            onChange={ this.handleChange } />
          </Col>
          <Col sm={3}>
          <Input type="select" name="afterAgoUnit"
            value={ this.state.data.afterAgoUnit }
            onChange={ this.handleChange }>
            <option value='m'>Minutes</option>
            <option value='h'>Hours</option>
          </Input>
          </Col>
        </FormGroup>
        <FormGroup row>
          <Label for="beforeAgo" sm={2}>Before</Label>
          <Col sm={3}>
          <Input type="number" step="1" name="beforeAgo"
            value={this.state.data.beforeAgo }
            onChange={ this.handleChange } />
          </Col>
          <Col sm={3}>
          <Input type="select" name="beforeAgoUnit"
            value={ this.state.data.beforeAgoUnit }
            onChange={ this.handleChange }>
            <option value='m'>Minutes</option>
            <option value='h'>Hours</option>
          </Input>
          </Col>
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
            <Input type="text" name="host1"
              value={ this.state.data.host1 }
              onChange={ this.handleChange }
              placeholder="IP (e.g 192.168.100.1)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="host2" sm={2}>Second Host</Label>
            <Col sm={6}>
            <Input type="text" name="host2"
              value={ this.state.data.host2 }
              onChange={ this.handleChange }
              placeholder="IP (e.g 192.168.100.1)" />
            </Col>
          </FormGroup>
        </TabPane>
        <TabPane tabId="2">
          <FormGroup row>
            <Label for="net1" sm={2}>First Net</Label>
            <Col sm={6}>
            <Input type="text" name="net1"
             value={ this.state.data.net1 }
             onChange={ this.handleChange }
             placeholder="Network (e.g. 192.168.100.0/24)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="net2" sm={2}>Second Net</Label>
            <Col sm={6}>
            <Input type="text" name="net2"
             value={ this.state.data.net2 }
             onChange={ this.handleChange }
             placeholder="Network (e.g. 192.168.100.0/24)" />
            </Col>
          </FormGroup>
        </TabPane>
        </TabContent>
        </div>

        <div style={{ padding: '.5rem' }}>
          <FormGroup row>
            <Label for="port1" sm={2}>First Port</Label>
            <Col sm={6}>
            <Input type="number" name="port1"
              value={ this.state.data.port1 }
              onChange={ this.handleChange }
              placeholder="Port number (e.g. 1-65535)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="port2" sm={2}>Second Port</Label>
            <Col sm={6}>
            <Input type="number" name="port2"
              value={ this.state.data.port2 }
              onChange={ this.handleChange }
             placeholder="Port number (e.g. 1-65535)" />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="protoName" sm={2}>Protocol</Label>
            <Col sm={6}>
            <Input type="select" name="protoName"
              value={ this.state.data.protoName }
              onChange={ this.handleChange }>
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
            <Input type="number" name="limitPackets"
             value={ this.state.data.limitPackets }
             onChange={ this.handleChange } />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="limitBytes" sm={2}>Limit Bytes</Label>
            <Col sm={6}>
            <Input type="number" name="limitBytes"
             value={ this.state.data.limitBytes }
             onChange={ this.handleChange } />
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="proto" sm={2}>Protocol Number</Label>
            <Col sm={6}>
            <Input type="number" name="proto"
             value={ this.state.data.proto }
             onChange={ this.handleChange }
             placeholder="IP Protocol Number (e.g. 0-255)"/>
            </Col>
          </FormGroup>
          <FormGroup row>
            <Label for="ignoreWeight" sm={2}>Ignore Query Weight</Label>
            <Col sm={6}>
            <FormGroup check>
              <Label check>
              <Input type="checkbox" name="ignoreWeight"
               checked={ this.state.data.ignoreWeight }
               onChange={ this.handleChange } />
              </Label>
            </FormGroup>
            </Col>
          </FormGroup>
          </Collapse>
          </div>
          </CardBody>
          <CardFooter>
            <Button type="submit" size="sm" color="primary"><i className="fa fa-dot-circle-o"></i> Submit</Button>
            <Button type="reset" onClick={this.handleReset} size="sm" color="danger"><i className="fa fa-ban"></i> Reset</Button>
          </CardFooter>
          </Form>
        </Card>
      </div>
    )
  }
}

export default Query;
