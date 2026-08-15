import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Operations from '@/views/Operations.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/operations',
    children: [
      {
        path: 'operations',
        name: 'Operations',
        component: Operations,
        meta: { title: '运维监控' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/Knowledge.vue'),
        meta: { title: '知识库' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '报告写作' },
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('@/views/Devices.vue'),
        meta: { title: '设备数据' },
      },
      {
        path: 'news',
        name: 'News',
        component: () => import('@/views/News.vue'),
        meta: { title: '环保资讯' },
      },
      {
        path: 'agent',
        name: 'Agent',
        component: () => import('@/views/Agent.vue'),
        meta: { title: '智能助手' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/Alerts.vue'),
        meta: { title: '实时告警' },
      },
      {
        path: 'compliance',
        name: 'Compliance',
        component: () => import('@/views/Compliance.vue'),
        meta: { title: '合规检查' },
      },
      {
        path: 'compare',
        name: 'Compare',
        component: () => import('@/views/Compare.vue'),
        meta: { title: '标准对比' },
      },
      {
        path: 'import',
        name: 'Import',
        component: () => import('@/views/Import.vue'),
        meta: { title: '数据导入' },
      },
      {
        path: 'tenant',
        name: 'Tenant',
        component: () => import('@/views/Tenant.vue'),
        meta: { title: '租户管理' },
      },
      {
        path: 'graph',
        name: 'Graph',
        component: () => import('@/views/Graph.vue'),
        meta: { title: '知识图谱' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
