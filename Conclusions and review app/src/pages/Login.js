/* eslint-disable prettier/prettier */
// material
import { styled, createTheme, ThemeProvider } from '@mui/material/styles';
import { Card, Stack, Container, Typography } from '@mui/material';
// layouts
import { LoadingButton } from '@mui/lab';
// components
import Page from '../components/Page';
// import { MHidden } from '../components/@material-extend';
// ----------------------------------------------------------------------

const theme = createTheme({
  palette: {
    primary: {
      main: '#0f0957',
      darker: '#080430',
    },
  },
});

const RootStyle = styled(Page)(({ theme }) => ({
  [theme.breakpoints.up('md')]: {
    display: 'flex'
  }
}));

const SectionStyle = styled(Card)(({ theme }) => ({
  width: '100%',
  maxWidth: 464,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  margin: theme.spacing(2, 0, 2, 2)
}));

const ContentStyle = styled('div')(({ theme }) => ({
  maxWidth: 480,
  margin: 'auto',
  display: 'flex',
  minHeight: '100vh',
  flexDirection: 'column',
  justifyContent: 'center',
  padding: theme.spacing(12, 0)
}));

// ----------------------------------------------------------------------

export default function Login({ _signIn }) {
  return (
    <RootStyle title="Login | ScanCode.io">
      {/* <MHidden width="mdDown">  This does not work due to Asgardeo conflict. FIX */}
      <Container maxWidth="md">
        <ContentStyle>
          <Stack sx={{ mb: 50 }}>
            <SectionStyle>
              <Typography variant="h4" sx={{ px: 5, mt: 10, mb: 5 }}>
                Hi, Welcome Back
              </Typography>
              <img src="/static/illustrations/scanCode.png" alt="login" />
            </SectionStyle>
          </Stack>
        </ContentStyle>

        {/* </MHidden> */}
      </Container>

      <Container maxWidth="sm">
        <ContentStyle>
          <Stack sx={{ mb: 5 }}>
            <Typography variant="h4" gutterBottom>
              Sign in to Conclusions and Review App
            </Typography>
            <Typography sx={{ color: 'text.secondary' }}>Click the login button below.</Typography>
          </Stack>
          <Stack sx={{ mb: 25 }}>
          <ThemeProvider theme={theme}>
            <LoadingButton
              color='primary'
              fullWidth
              size="large"
              type="submit"
              variant="contained"
              onClick={_signIn}
            >
              Login
            </LoadingButton>
            </ThemeProvider>
          </Stack>
        </ContentStyle>
      </Container>
    </RootStyle>
  );
}
