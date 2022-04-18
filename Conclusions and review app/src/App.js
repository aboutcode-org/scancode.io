// material
import { Button } from '@mui/material';
// routes
import { useAuthContext } from '@asgardeo/auth-react';
import React, { useState } from 'react';
import Router from './routes';
// theme
import ThemeConfig from './theme';
import GlobalStyles from './theme/globalStyles';
// components
import ScrollToTop from './components/ScrollToTop';
import { BaseOptionChartStyle } from './components/charts/BaseOptionChart';
// login page
import Login from './pages/Login';
// ----------------------------------------------------------------------

export default function App() {
  // These codes correspond to the Asgardeo. You can easily enable a secure authentication using Asgardeo.
  // Take a look at what is Asgardeo if you are not aware of that using the link below
  // http://asgardeo.io/

  // const { state, signIn, signOut } = useAuthContext();

  // const _signIn = () => {
  //   signIn();
  // };

  return (
    <div className="App">
      {/* {state.isAuthenticated ? ( */}
      <ThemeConfig>
        <ScrollToTop />
        <GlobalStyles />
        <BaseOptionChartStyle />
        <Router />
      </ThemeConfig>
      {/* ) : ( <Login _signIn={_signIn} /> */}
      {/* )} */}
    </div>
  );
}
