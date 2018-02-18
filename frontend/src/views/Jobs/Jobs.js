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
import {Card, CardHeader, CardBody, Table} from 'reactstrap';

class Jobs extends Component {
  constructor() {
    super();
    this.state = {
      jobs: [],
      status: {},
      urls: {},
    };
  }

  componentDidMount() {
    var Config = require('Config');

    var statusApi = fetch( Config.serverUrl + '/status/' )
      .then(results => {
        return results.json();
      })

    var urlsApi = fetch( Config.serverUrl + '/urls/' )
      .then(results => {
        return results.json();
      })

    Promise.all([statusApi, urlsApi]).then( values => {
      var status = values[0];
      var urls = values[1];

      this.setState({'status': status, 'urls': urls});

      let jobs = Object.entries(status).map(([key, value], index) => {
        return (
          <tr key={ key }>
            <th scope="row">{ index + 1 }</th>
              <td>{ value.events[0][0] }</td>
            <td>{key}</td>
            <td>TODO - Query</td>
            <td>{ value.state }</td>
            <td>{ key in urls ? <a href={ urls[key] }>Get PCAP</a> : "Unavailable"}</td>
          </tr>
        )
      })
      this.setState({'jobs': jobs});
    })
  }

  render() {
    /* Use jQuery to retrieve job data */

    return (
      <div className="animated fadeIn">
        <Card>
        <CardBody>
        <Table striped>
          <thead><tr>
            <th>#</th>
            <th>Request Time</th>
            <th>ID</th>
            <th>Query</th>
            <th>State</th>
            <th>URL</th>
          </tr></thead>
          <tbody>
          { this.state.jobs }
          </tbody>
        </Table>
        </CardBody>
        </Card>
      </div>
    )
  }
}

export default Jobs;
