import React, {Component} from 'react';

class Footer extends Component {
  render() {
    return (
      <footer className="app-footer">
        <span><a href="http://github.com/rocknsm/docket">Docket</a> &copy; 2018 <a href="http://rocknsm.io/">RockNSM</a></span>
        <span className="ml-auto">Powered by <a href="http://coreui.io">CoreUI</a></span>
      </footer>
    )
  }
}

export default Footer;
