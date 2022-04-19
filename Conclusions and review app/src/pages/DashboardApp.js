// material
import { Box, Grid, Container, Typography } from '@mui/material';
// components
import Page from '../components/Page';
import {
  AppTasks,
  AppWidgets6,
  AppWidgets1,
  AppWidgets8,
  AppWidgets7,
  AppWidgets2,
  AppWidgets5,
  AppWidgets9,
  AppWidgets3,
  AppWidgets4,
  AppWidgets10,
  AppWidgets11
} from '../components/_dashboard/app';

// ----------------------------------------------------------------------

export default function DashboardApp() {
  return (
    <Page title="Dashboard | ScanCode.io">
      <Container maxWidth="xl">
        <Box sx={{ pb: 5 }}>
          <Typography variant="h4">Hi, Welcome back</Typography>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <AppWidgets2 />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <AppWidgets6 />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <AppWidgets8 />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <AppWidgets1 />
          </Grid>

          <Grid item xs={12} md={6} lg={8}>
            <AppWidgets3 />
          </Grid>

          <Grid item xs={12} md={6} lg={4}>
            <AppWidgets9 />
          </Grid>

          <Grid item xs={12} md={6} lg={8}>
            <AppWidgets11 />
          </Grid>

          <Grid item xs={12} md={6} lg={4}>
            <AppWidgets10 />
          </Grid>

          <Grid item xs={12} md={6} lg={8}>
            <AppWidgets7 />
          </Grid>

          <Grid item xs={12} md={6} lg={4}>
            <AppWidgets5 />
          </Grid>

          <Grid item xs={12} md={6} lg={4}>
            <AppWidgets4 />
          </Grid>

          <Grid item xs={12} md={6} lg={8}>
            <AppTasks />
          </Grid>
        </Grid>
      </Container>
    </Page>
  );
}
