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
import { Link } from 'react-router-dom';
import {Card, CardHeader, CardBody, Table} from 'reactstrap';

class Jobs extends Component {
  constructor() {
    super();
    this.state = {
      jobs: [],
      entries: [],
      urls: {},
      interval: null,
    };

    this.updateTable = this.updateTable.bind(this);
  }

  updateTable() {
    var Config = require('Config');

    var statusApi = fetch( Config.serverUrl + '/jobs/' )
      .then(results => {
        return results.json();
      })

    var urlsApi = fetch( Config.serverUrl + '/urls/' )
      .then(results => {
        return results.json();
      })

    Promise.all([statusApi, urlsApi]).then( values => {
      var jobs = values[0];
      var urls = values[1];

      console.log(urls)

      jobs.sort(function(a,b) { return (a.time > b.time) });

      this.setState({'jobs': jobs, 'urls': urls});

      let entries = Object.entries(jobs).map((entry, index) => {

        return (
          <tr key={ entry[1].id }>
            <th scope="row">{ index + 1 }</th>
              <td>{ entry[1].time }</td>
            <td>{
              <Link to={"/status/"+entry[1].id}
                title={"Status for " + entry[1].id.substring(0, 6) }>
                {entry[1].id.substring(0, 6)}
              </Link>
           }</td>
            <td>{ entry[1].query }</td>
            <td>{ entry[1].state }</td>
            <td>{ entry[1].id in urls ? <Link to={ urls[entry[1].id] }>Get PCAP</Link> : "Unavailable"}</td>
          </tr>
        )
      })

      this.setState({'entries': entries});
    })
  }

  componentDidMount() {
    this.interval = setInterval(this.updateTable, 1000);
  }

  componentWillUnmount() {
    clearInterval(this.interval);
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
          { this.state.entries }
          </tbody>
        </Table>
        </CardBody>
        </Card>
      </div>
    )
  }
}

export default Jobs;
