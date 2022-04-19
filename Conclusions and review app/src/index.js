import React from 'react';
import { render } from 'react-dom';
import { AuthProvider } from '@asgardeo/auth-react';

// scroll bar
import 'simplebar/src/simplebar.css';

// import ReactDOM from 'react-dom';
import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';

import App from './App';

// ----------------------------------------------------------------------

const Index = () => (
  // These codes correspond to the Asgardeo. You can easily enable a secure authentication using Asgardeo.
  // Take a look at what is Asgardeo if you are not aware of that using the link below
  // http://asgardeo.io/

  // <AuthProvider
  //   config={{
  //     signInRedirectURL: 'http://localhost:5000',
  //     signOutRedirectURL: 'http://localhost:5000',
  //     clientID: '',
  //     serverOrigin: '',
  //     scope: ['openid', 'profile']
  //   }}
  // >
  <HelmetProvider>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </HelmetProvider>
  // </AuthProvider>
);

render(<Index />, document.getElementById('root'));
