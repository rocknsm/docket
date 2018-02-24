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
import React, {Component} from 'react';

class SidebarMinimizer extends Component {

  sidebarMinimize() {
    document.body.classList.toggle('sidebar-minimized');
  }

  brandMinimize() {
    document.body.classList.toggle('brand-minimized');
  }

  render() {
    return (
      <button className="sidebar-minimizer" type="button" onClick={(event) => { this.sidebarMinimize(); this.brandMinimize() }}></button>
    )
  }
}

export default SidebarMinimizer;
