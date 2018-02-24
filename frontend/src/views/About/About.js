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
import {Card, CardHeader, CardBody, ListGroup, ListGroupItem, ListGroupItemText, ListGroupItemHeading} from 'reactstrap';

class About extends Component {

  render() {
    return (
      <div className="animated fadeIn">
        <Card>
          <CardHeader>
          About Docket
          </CardHeader>
          <CardBody>
          Docket was created as part of the <a href="http://rocknsm.io">RockNSM
          project</a>. It provides an a front-end to the execellent <a
           href="http://github.com/google/stenographer/">Google Stenographer
          </a>. For more information, visit the Docket <a
          href="https://github.com/rocknsm/docket/">GitHub</a> page.
          </CardBody>
        </Card>
        <Card>
        <CardHeader>
        Looking for Help?
        </CardHeader>
        <CardBody>
        Check out the forums over at <a
         href="http://community.rocknsm.io">community.rocknsm.io</a>
        </CardBody>
        </Card>

        <Card>
        <CardHeader>
        Third Party Software
        </CardHeader>
        <CardBody>
        <p>This application uses source code from the following projects:</p>

        <ListGroup>
        <ListGroupItem>
        <ListGroupItemHeading>
          <a href="https://github.com/mrholek/CoreUI-React/">CoreUI - React</a>
        </ListGroupItemHeading>
        <ListGroupItemText>
          Copyright (c) 2018 creativeLabs Łukasz Holeczek.
        </ListGroupItemText>
        </ListGroupItem>
        </ListGroup>
        </CardBody>
        </Card>
      </div>
    )
  }
}

export default About;
