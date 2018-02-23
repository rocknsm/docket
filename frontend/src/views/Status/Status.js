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
import {Link} from 'react-router-dom';
import {Card, CardHeader, CardBody, Table} from 'reactstrap';

class Status extends Component {
  constructor(props) {
    super(props);

    this.state = {
      queryId: props.match.params.queryId,
      entries: [],
      status: {state:'Loading...'},
      url: null,
    };

    this.updateTable = this.updateTable.bind(this);

  }

  updateTable() {
    var Config = require('Config');

    var statusApi = fetch( Config.serverUrl + '/status/' + this.state.queryId )
      .then(results => {
        return results.json();
      })

    var urlsApi = fetch( Config.serverUrl + '/urls/' + this.state.queryId )
      .then(results => {
        return results.json();
      })

    Promise.all([statusApi, urlsApi]).then( values => {
      console.log("Values", values);

      var status = values[0][this.state.queryId];
      var urls = values[1];

      status['events'].sort(function(a,b) { return (a.datetime > b.datetime) });

      let url = null;
      if (this.state.queryId in urls)
        url = urls[this.state.queryId];

      let totalSize = 0;
      if ( status['state'] === 'Completed' ) {
        status['successes'].forEach( (element) => {
          totalSize += isNaN(element['value']) ? 0 : element['value'];
        } )
      }

      console.log("totalSize", totalSize);

      this.setState({'status': status, 'url': url, 'resultSize': totalSize});

      let entries = Object.entries(status['events']).map((entry, index) => {

        console.log("Entry", entry);

        return (
          <tr key={ index }>
            <th scope="row">{ index + 1 }</th>
              <td>{ entry[1].datetime }</td>
            <td>{ entry[1].name }</td>
            <td>{ entry[1].msg }</td>
            <td>{ entry[1].state }</td>
          </tr>
        );
      })

      this.setState({'entries': entries});
      if ( status['state'] === 'Completed' || status['state'] === 'Failed' )
        clearInterval(this.interval);
    })
  }

  componentDidMount() {
    this.interval = setInterval(this.updateTable, 1000);
  }

  componentWillUnmount() {
    clearInterval(this.interval);
  }

  render() {
    const prettyBytes = require('pretty-bytes');
    /* Use jQuery to retrieve job data */

    return (
      <div className="animated fadeIn">
        <Card>
        <CardHeader><h2>Status for {this.state.queryId}</h2></CardHeader>
        <CardBody>
        <h3>Overview</h3>
        <dl>
          <dt>Overall State</dt>
          <dd>{this.state.status.state}</dd>
          <dt>Download Result</dt>
          <dd>{ (this.state.url !== null) ?
                <div><a href={this.state.url}>Get PCAP</a>
                <p>({ prettyBytes(this.state.resultSize) })</p></div> :
                <div>Unavailable</div> }</dd>
        </dl>
        <h3>Details</h3>
        <Table striped>
          <thead><tr>
            <th>#</th>
            <th>Event Time</th>
            <th>Name</th>
            <th>Message</th>
            <th>State</th>
          </tr></thead>
          <tbody>
          { this.state.entries }
          </tbody>
        </Table>        </CardBody>
        </Card>
      </div>
    )
  }
}

export default Status;
