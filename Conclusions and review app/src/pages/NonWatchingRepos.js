/* eslint-disable no-template-curly-in-string */
import { filter } from 'lodash';
import { Icon } from '@iconify/react';
import { useEffect, useState } from 'react';
import plusFill from '@iconify/icons-eva/plus-fill';
import { Link as RouterLink } from 'react-router-dom';
import CircularProgress from '@mui/material/CircularProgress';

// material
import {
  Card,
  Table,
  Stack,
  Button,
  Checkbox,
  TableRow,
  TableBody,
  TableCell,
  Container,
  Typography,
  TableContainer,
  TablePagination,
  Link
} from '@mui/material';

// components
import axios from 'axios';
import Page from '../components/Page';
import Label from '../components/Label';
import Scrollbar from '../components/Scrollbar';
import SearchNotFound from '../components/SearchNotFound';
import { RepoListHead, RepoListToolbar, RepoMoreMenu } from '../components/_dashboard/repos';

// ----------------------------------------------------------------------

// This ORG_ID is the id of Github Organization nexB. Feel free to change it appropriately.
const ORG_ID = 'MDEyOk9yZ2FuaXphdGlvbjEwNzg5OTY3';
const API_BASE_URL = process.env.YOUR_API_BASE_URL;
const API_TOKEN = process.env.YOUR_API_TOKEN;

const TABLE_HEAD = [
  { id: 'repoName', label: 'Name', alignRight: false },
  { id: 'createdAt', label: 'Created At', alignRight: false },
  { id: 'updatedAt', label: 'Updated At', alignRight: false },
  { id: 'monitorStatus', label: 'State', alignRight: false },
  { id: '' }
];

// ----------------------------------------------------------------------

function descendingComparator(a, b, orderBy) {
  if (b[orderBy] < a[orderBy]) {
    return -1;
  }
  if (b[orderBy] > a[orderBy]) {
    return 1;
  }
  return 0;
}

function getComparator(order, orderBy) {
  return order === 'desc'
    ? (a, b) => descendingComparator(a, b, orderBy)
    : (a, b) => -descendingComparator(a, b, orderBy);
}

function applySortFilter(array, comparator, query) {
  const stabilizedThis = array.map((el, index) => [el, index]);
  stabilizedThis.sort((a, b) => {
    const order = comparator(a[0], b[0]);
    if (order !== 0) return order;
    return a[1] - b[1];
  });
  if (query) {
    return filter(
      array,
      (_repo) => _repo.repoName.toLowerCase().indexOf(query.toLowerCase()) !== -1
    );
  }
  return stabilizedThis.map((el) => el[0]);
}

export default function User() {
  const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      Authorization: `Bearer ${API_TOKEN}`
    }
  });

  const [apiData, setApiData] = useState([]);
  const [loading, setLoading] = useState(false);

  const startSpinner = () => {
    setLoading(true);
  };
  const stopSpinner = () => {
    setLoading(false);
  };
  const clearApiData = () => {
    setApiData([]);
  };

  async function getNonMonitoringRepos() {
    startSpinner();
    api.get(`/getNonMonitoringRepos/${ORG_ID}`).then((getData) => {
      console.log(getData.data);
      setApiData(getData.data);
      stopSpinner();
    });
  }

  useEffect(() => {
    getNonMonitoringRepos();
  }, []);

  const getLatestApiData = () => {
    getNonMonitoringRepos();
  };

  let REPOLIST = [];
  REPOLIST = apiData;

  const [page, setPage] = useState(0);
  const [order, setOrder] = useState('asc');
  const [selected, setSelected] = useState([]);
  const [orderBy, setOrderBy] = useState('repoName');
  const [filterName, setFilterName] = useState('');
  const [rowsPerPage, setRowsPerPage] = useState(5);

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleSelectAllClick = (event) => {
    if (event.target.checked) {
      const newSelecteds = REPOLIST.map((n) => n.repoName);
      console.log('newSelecteds');
      console.log(REPOLIST);
      setSelected(newSelecteds);
      return;
    }
    setSelected([]);
  };

  const handleClick = (event, repoName) => {
    const selectedIndex = selected.indexOf(repoName);
    let newSelected = [];
    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, repoName);
    } else if (selectedIndex === 0) {
      newSelected = newSelected.concat(selected.slice(1));
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.concat(selected.slice(0, -1));
    } else if (selectedIndex > 0) {
      newSelected = newSelected.concat(
        selected.slice(0, selectedIndex),
        selected.slice(selectedIndex + 1)
      );
    }
    setSelected(newSelected);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleFilterByName = (event) => {
    setFilterName(event.target.value);
  };

  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - REPOLIST.length) : 0;

  const filteredUsers = applySortFilter(REPOLIST, getComparator(order, orderBy), filterName);

  const isRepoNotFound = filteredUsers.length === 0;

  return (
    <Page title="Non Watching Projects | ScanCode.io">
      <Container>
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={5}>
          <Typography variant="h4" gutterBottom>
            Non Watching Projects
          </Typography>
          <Button
            variant="contained"
            component={RouterLink}
            to="#"
            startIcon={<Icon icon={plusFill} />}
          >
            Add Project
          </Button>
        </Stack>

        <Card>
          <RepoListToolbar
            numSelected={selected.length}
            filterName={filterName}
            onFilterName={handleFilterByName}
          />

          <Scrollbar>
            <TableContainer sx={{ minWidth: 800 }}>
              <Table>
                <RepoListHead
                  order={order}
                  orderBy={orderBy}
                  headLabel={TABLE_HEAD}
                  rowCount={REPOLIST.length}
                  numSelected={selected.length}
                  onRequestSort={handleRequestSort}
                  onSelectAllClick={handleSelectAllClick}
                />
                <TableBody>
                  {filteredUsers
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((row) => {
                      const { id, repoName, updatedAt, monitorStatus, createdAt, repoUrl } = row;
                      const isItemSelected = selected.indexOf(repoName) !== -1;

                      return (
                        <TableRow
                          hover
                          key={id}
                          tabIndex={-1}
                          role="checkbox"
                          selected={isItemSelected}
                          aria-checked={isItemSelected}
                        >
                          <TableCell padding="checkbox">
                            <Checkbox
                              checked={isItemSelected}
                              onChange={(event) => handleClick(event, repoName)}
                            />
                          </TableCell>
                          <TableCell component="th" scope="row" padding="none">
                            <Stack direction="row" alignItems="center" spacing={2}>
                              <Typography
                                variant="subtitle2"
                                noWrap
                                component={Link}
                                target="_blank"
                                href={repoUrl}
                              >
                                {repoName}
                              </Typography>
                            </Stack>
                          </TableCell>
                          <TableCell align="left">{createdAt}</TableCell>
                          <TableCell align="left">{updatedAt}</TableCell>
                          <TableCell align="left">
                            <Label
                              variant="ghost"
                              color={(monitorStatus === '0' && 'error') || 'success'}
                            >
                              {monitorStatus === '1' ? 'Watch' : 'Unwatch'}
                            </Label>
                          </TableCell>

                          <TableCell align="right">
                            <RepoMoreMenu
                              getLatestApiData={getLatestApiData}
                              clearApiData={clearApiData}
                              startSpinner={startSpinner}
                              id={id}
                              orgId={ORG_ID}
                              repoName={repoName}
                              updatedAt={updatedAt}
                              monitorStatus={monitorStatus}
                              createdAt={createdAt}
                              repoUrl={repoUrl}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  {emptyRows > 0 && (
                    <TableRow style={{ height: 53 * emptyRows }}>
                      <TableCell colSpan={6} />
                    </TableRow>
                  )}
                </TableBody>
                {!loading && isRepoNotFound && (
                  <TableBody>
                    <TableRow>
                      <TableCell align="center" colSpan={6} sx={{ py: 3 }}>
                        <SearchNotFound searchQuery={filterName} />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                )}
                {loading && (
                  <TableBody>
                    <TableRow>
                      <TableCell align="center" colSpan={6} sx={{ py: 3 }}>
                        <CircularProgress />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                )}
              </Table>
            </TableContainer>
          </Scrollbar>

          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={REPOLIST.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </Card>
      </Container>
    </Page>
  );
}
