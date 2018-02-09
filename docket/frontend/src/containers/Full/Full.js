import React, {Component} from 'react';
import {Link, Switch, Route, Redirect} from 'react-router-dom';
import {Container} from 'reactstrap';
import Header from '../../components/Header/';
import Sidebar from '../../components/Sidebar/';
import Breadcrumb from '../../components/Breadcrumb/';
import Footer from '../../components/Footer/';

import Query from '../../views/Query/';
import Jobs from '../../views/Jobs/';
import Stats from '../../views/Stats/';
import About from '../../views/About/';

class Full extends Component {
  render() {
    return (
      <div className="app">
        <Header />
        <div className="app-body">
          <Sidebar {...this.props}/>
          <main className="main">
            <Breadcrumb />
            <Container fluid>
              <Switch>
                <Route path="/query" name="Query" component={Query}/>
                <Route path="/jobs" name="Jobs" component={Jobs}/>
                <Route path="/stats" name="Stats" component={Stats}/>
                <Route path="/about" name="About" component={About}/>
                <Redirect from="/" to="/query"/>
              </Switch>
            </Container>
          </main>
        </div>
        <Footer />
      </div>
    );
  }
}

export default Full;
