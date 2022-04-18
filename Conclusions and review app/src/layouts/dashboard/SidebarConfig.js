import { Icon } from '@iconify/react';
import pieChart2Fill from '@iconify/icons-eva/pie-chart-2-fill';
import shoppingBagFill from '@iconify/icons-eva/shopping-bag-fill';
import fileTextFill from '@iconify/icons-eva/file-text-fill';
import alertTriangleFill from '@iconify/icons-eva/alert-triangle-fill';

// ----------------------------------------------------------------------

const getIcon = (name) => <Icon icon={name} width={22} height={22} />;

const sidebarConfig = [
  {
    title: 'dashboard',
    path: '/dashboard/app',
    icon: getIcon(pieChart2Fill)
  },
  {
    title: 'All Projects',
    path: '/dashboard/allRepos',
    icon: getIcon(shoppingBagFill)
  },
  {
    title: 'watching Projects',
    path: '/dashboard/watchingRepos',
    icon: getIcon(fileTextFill)
  },
  {
    title: 'non Watching Projects',
    path: '/dashboard/nonWatchingRepos',
    icon: getIcon(alertTriangleFill)
  }
];

export default sidebarConfig;
