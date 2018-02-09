import React, { Component } from 'react';
import {Card, CardHeader, CardBody} from 'reactstrap';

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
        <CardBody>
        This application uses the following open source projects:
        </CardBody>
        </Card>
      </div>
    )
  }
}

export default About;
