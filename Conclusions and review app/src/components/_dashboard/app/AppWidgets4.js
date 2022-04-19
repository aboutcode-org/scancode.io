import faker from 'faker';
import PropTypes from 'prop-types';
import { Icon } from '@iconify/react';
// import googleFill from '@iconify/icons-eva/google-fill';
// import twitterFill from '@iconify/icons-eva/twitter-fill';
// import facebookFill from '@iconify/icons-eva/facebook-fill';
// import linkedinFill from '@iconify/icons-eva/linkedin-fill';
import bugFilled from '@iconify/icons-ant-design/bug-filled';
// material
import { Box, Grid, Card, Paper, Typography, CardHeader, CardContent } from '@mui/material';
// utils
import { fShortenNumber } from '../../../utils/formatNumber';

// ----------------------------------------------------------------------

const SOCIALS = [
  {
    name: 'Scans',
    value: faker.datatype.number(),
    icon: <Icon icon={bugFilled} color="#1877F2" width={32} height={32} />
  },
  {
    name: 'Scans',
    value: faker.datatype.number(),
    icon: <Icon icon={bugFilled} color="#DF3E30" width={32} height={32} />
  },
  {
    name: 'Scans',
    value: faker.datatype.number(),
    icon: <Icon icon={bugFilled} color="#006097" width={32} height={32} />
  },
  {
    name: 'Scans',
    value: faker.datatype.number(),
    icon: <Icon icon={bugFilled} color="#1C9CEA" width={32} height={32} />
  }
];

// ----------------------------------------------------------------------

SiteItem.propTypes = {
  site: PropTypes.object
};

function SiteItem({ site }) {
  const { icon, value, name } = site;

  return (
    <Grid item xs={6}>
      <Paper variant="outlined" sx={{ py: 2.5, textAlign: 'center' }}>
        <Box sx={{ mb: 0.5 }}>{icon}</Box>
        <Typography variant="h6">{fShortenNumber(value)}</Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {name}
        </Typography>
      </Paper>
    </Grid>
  );
}

export default function AppWidgets4() {
  return (
    <Card>
      <CardHeader title="ScanCode Conclusions" />
      <CardContent>
        <Grid container spacing={2}>
          {SOCIALS.map((site) => (
            <SiteItem key={site.name} site={site} />
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}
