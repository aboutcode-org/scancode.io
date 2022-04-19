import { Icon } from '@iconify/react';
import { useRef, useState } from 'react';
import editFill from '@iconify/icons-eva/edit-fill';
import { Link as RouterLink } from 'react-router-dom';
import trash2Outline from '@iconify/icons-eva/trash-2-outline';
import moreVerticalFill from '@iconify/icons-eva/more-vertical-fill';
import axios from 'axios';
// material
import { Menu, MenuItem, IconButton, ListItemIcon, ListItemText } from '@mui/material';

// ----------------------------------------------------------------------
// This ORG_ID is the id of Github Organization nexB. Feel free to change it appropriately.
const ORG_ID = 'MDEyOk9yZ2FuaXphdGlvbjEwNzg5OTY3';
const API_BASE_URL = process.env.YOUR_API_BASE_URL;
const API_TOKEN = process.env.YOUR_API_TOKEN;

export default function RepoMoreMenu(props) {
  const ref = useRef(null);
  const [isOpen, setIsOpen] = useState(false);

  const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      Authorization: `Bearer ${API_TOKEN}`
    }
  });
  const sendDataToAPI = (id, orgId, repoName, repoUrl, createdAt, updatedAt, monitorStatus) => {
    api
      .put(`/changeMonitorStatus/${ORG_ID}/${id}/${monitorStatus === '1' ? 1 : 0}`, {
        id,
        createdAt,
        orgId,
        repoName,
        repoUrl,
        updatedAt
      })
      .then(() => {
        props.getLatestApiData();
      });
  };

  return (
    <>
      <IconButton ref={ref} onClick={() => setIsOpen(true)}>
        <Icon icon={moreVerticalFill} width={20} height={20} />
      </IconButton>

      <Menu
        open={isOpen}
        anchorEl={ref.current}
        onClose={() => setIsOpen(false)}
        PaperProps={{
          sx: { width: 200, maxWidth: '100%' }
        }}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem
          sx={{ color: 'text.secondary' }}
          onClick={() => {
            setIsOpen(false);
            sendDataToAPI(
              props.id,
              props.orgId,
              props.repoName,
              props.repoUrl,
              props.createdAt,
              props.updatedAt,
              '1'
            );

            props.clearApiData();
            props.startSpinner();
          }}
        >
          <ListItemIcon>
            <Icon icon={editFill} width={24} height={24} />
          </ListItemIcon>
          <ListItemText primary="Watch" primaryTypographyProps={{ variant: 'body2' }} />
        </MenuItem>

        <MenuItem
          sx={{ color: 'text.secondary' }}
          onClick={() => {
            setIsOpen(false);
            sendDataToAPI(
              props.id,
              props.orgId,
              props.repoName,
              props.repoUrl,
              props.createdAt,
              props.updatedAt,
              '0'
            );
            props.clearApiData();
            props.startSpinner();
          }}
        >
          <ListItemIcon>
            <Icon icon={trash2Outline} width={24} height={24} />
          </ListItemIcon>
          <ListItemText primary="Unwatch" primaryTypographyProps={{ variant: 'body2' }} />
        </MenuItem>
      </Menu>
    </>
  );
}
