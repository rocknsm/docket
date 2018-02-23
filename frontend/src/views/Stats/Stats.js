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
import {Card, CardHeader, CardBody, ListGroup, ListGroupItem, ListGroupItemHeading, ListGroupItemText} from 'reactstrap';

class Stats extends Component {
  constructor() {
    super();
    this.state = {
      interval: null,
    };

    this.updateData = this.updateData.bind(this);
  }

  updateData() {
    var Config = require('Config');

    var statsApi = fetch( Config.serverUrl + '/stats/' )
      .then(results => {
        return results.json();
      })

    Promise.all([statsApi, ]).then( values => {
      var stats = values[0];

      let entries
    })

    clearInterval(this.interval);

  }

  componentDidMount() {
    this.interval = setInterval(this.updateData, 1000);
  }

  componentWillUnmount() {
    clearInterval(this.interval);
  }

  render() {
    return (
      <div className="animated fadeIn">
      <Card>
      <CardHeader>
      Available Sensors
      </CardHeader>
      <CardBody>
      <ListGroup>
      <ListGroupItem>
      <ListGroupItemHeading>
        sensor-001
      </ListGroupItemHeading>
      <ListGroupItemText>
        Oldest PCAP: blah
      </ListGroupItemText>
      </ListGroupItem>
      </ListGroup>
      </CardBody>
      </Card>      </div>
    )
  }
}

export default Stats;
