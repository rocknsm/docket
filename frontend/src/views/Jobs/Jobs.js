import React, { Component } from 'react';
import {Card, CardHeader, CardBody, Table} from 'reactstrap';

class Jobs extends Component {

  render() {
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
            <tr>
              <th scope="row">1</th>
              <td>2018-02-09 17:45:32</td>
              <td>abcdef-12345-67890</td>
              <td>host 1.2.3.4 and host 7.8.9.1</td>
              <td>Complete</td>
              <td><a href="#">abcdef-12345-67890.pcap</a></td>
            </tr>
          </tbody>
        </Table>
        </CardBody>
        </Card>
      </div>
    )
  }
}

export default Jobs;
