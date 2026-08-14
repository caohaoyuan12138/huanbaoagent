<template>
  <el-container class="main-content">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>
          <el-icon><Platform /></el-icon>
          <span>环保Agent</span>
        </h1>
        <p>化工行业环保智能助手</p>
      </div>
      <nav class="sidebar-menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="menu-item"
          :class="{ active: $route.path === item.path }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>
      <!-- 租户选择移至侧边栏底部 -->
      <div class="sidebar-footer">
        <div class="tenant-row">
          <el-icon><OfficeBuilding /></el-icon>
          <el-select
            v-model="currentTenantId"
            placeholder="选择租户"
            size="small"
            style="flex: 1"
            @change="onTenantChange"
          >
            <el-option label="全部租户" :value="''" />
            <el-option
              v-for="t in tenants"
              :key="t.id"
              :label="t.name"
              :value="String(t.id)"
            />
          </el-select>
        </div>
        <el-button size="small" style="width: 100%" @click="seedData">
          <el-icon><Refresh /></el-icon>
          <span style="margin-left: 4px">初始化数据</span>
        </el-button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <el-container>
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const router = useRouter()
const tenants = ref([])
const currentTenantId = ref(localStorage.getItem('currentTenantId') || '')

const loadTenants = async () => {
  try {
    tenants.value = await api.get('/tenants')
  } catch (e) {
    console.error('加载租户失败', e)
  }
}

const onTenantChange = async (val) => {
  if (!val) {
    localStorage.removeItem('currentTenantId')
    localStorage.removeItem('currentTenantCode')
    localStorage.removeItem('currentTenantName')
  } else {
    const t = tenants.value.find(x => String(x.id) === val)
    if (t) {
      localStorage.setItem('currentTenantId', val)
      localStorage.setItem('currentTenantCode', t.code)
      localStorage.setItem('currentTenantName', t.name)
    }
  }
  await loadTenants()
}

onMounted(() => {
  loadTenants()
})

const menuItems = [
  { path: '/dashboard', title: '仪表盘', icon: 'DataBoard' },
  { path: '/knowledge', title: '知识库', icon: 'Collection' },
  { path: '/reports', title: '报告写作', icon: 'Document' },
  { path: '/devices', title: '设备数据', icon: 'Monitor' },
  { path: '/alerts', title: '实时告警', icon: 'BellFilled' },
  { path: '/compliance', title: '合规检查', icon: 'Check' },
  { path: '/compare', title: '标准对比', icon: 'Ratio' },
  { path: '/import', title: '数据导入', icon: 'Upload' },
  { path: '/news', title: '环保资讯', icon: 'Bell' },
  { path: '/agent', title: '智能助手', icon: 'ChatDotRound' },
  { path: '/graph', title: '知识图谱', icon: 'Connection' },
  { path: '/tenant', title: '租户管理', icon: 'OfficeBuilding' },
]

const seedData = async () => {
  try {
    await api.post('/knowledge/seed')
    await api.post('/reports/seed')
    await api.post('/devices/seed')
    await api.post('/news/news/seed')
    ElMessage.success('数据初始化完成')
  } catch (error) {
    ElMessage.error('初始化失败: ' + (error.response?.data?.detail || error.message))
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.tenant-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.tenant-row .el-icon {
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
  flex-shrink: 0;
}
</style>
