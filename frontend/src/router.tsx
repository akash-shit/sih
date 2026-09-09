import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { SignInPage } from '@/pages/SignInPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { AOIPage } from '@/pages/AOIPage';
import { AOIDetailPage } from '@/pages/AOIDetailPage';
import { TileDetailPage } from '@/pages/TileDetailPage';
import { SearchPage } from '@/pages/SearchPage';
import { ChangesPage } from '@/pages/ChangesPage';
import { ChangeDetailPage } from '@/pages/ChangeDetailPage';
import { ReviewQueuePage } from '@/pages/ReviewQueuePage';
import { ClustersPage } from '@/pages/ClustersPage';
import { ClusterDetailPage } from '@/pages/ClusterDetailPage';
import { OnboardPage } from '@/pages/OnboardPage';
import { AuditLogPage } from '@/pages/AuditLogPage';
import { SettingsPage } from '@/pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/signin',
    element: <SignInPage />,
  },
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/signin" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'aois',
        element: <AOIPage />,
      },
      {
        path: 'explorer',
        element: <AOIPage />,
      },
      {
        path: 'aois/:aoiId',
        element: <AOIDetailPage />,
      },
      {
        path: 'tiles/:tileId',
        element: <TileDetailPage />,
      },
      {
        path: 'search',
        element: <SearchPage />,
      },
      {
        path: 'changes',
        element: <ChangesPage />,
      },
      {
        path: 'changes/:vectorId',
        element: <ChangeDetailPage />,
      },
      {
        path: 'change/:vectorId',
        element: <ChangeDetailPage />,
      },
      {
        path: 'review',
        element: <ReviewQueuePage />,
      },
      {
        path: 'clusters',
        element: <ClustersPage />,
      },
      {
        path: 'clusters/:clusterId',
        element: <ClusterDetailPage />,
      },
      {
        path: 'onboard',
        element: <OnboardPage />,
      },
      {
        path: 'admin/onboard',
        element: <OnboardPage />,
      },
      {
        path: 'audit-log',
        element: <AuditLogPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
]);
