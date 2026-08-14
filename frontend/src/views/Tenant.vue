<template>
  <div>
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h3>租户管理</h3>
        <el-tag :type="currentTenant ? 'success' : 'info'" size="small">
          {{ currentTenant ? currentTenant.name : '未选择租户' }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button size="small" @click="seedTenants">
          <el-icon><Refresh /></el-icon> 初始化数据
        </el-button>
        <el-button size="small" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon> 新增租户
        </el-button>
      </div>
    </div>

    <!-- 租户列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tenants" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="租户名称" min-width="160">
          <template #default="{ row }">
            <span style="font-weight: 500">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contact_name" label="联系人" width="100" />
        <el-table-column prop="contact_phone" label="电话" width="130" />
        <el-table-column prop="contact_email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="设备数" width="80">
          <template #default="{ row }">
            <span style="color: #4ade80; font-weight: 600">{{ row.device_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="告警数" width="80">
          <template #default="{ row }">
            <span :style="{ color: (row.alert_count || 0) > 0 ? '#f56c6c' : '#999', fontWeight: 600 }">
              {{ row.alert_count || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '暂停' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="switchTenant(row)">
              切换
            </el-button>
            <el-button size="small" link @click="openEdit(row)">
              编辑
            </el-button>
            <el-button size="small" link type="danger" @click="deleteTenant(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑租户' : '新增租户'"
      width="560px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        style="padding-right: 16px"
      >
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="租户名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入租户名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="租户编码" prop="code">
              <el-input v-model="form.code" :disabled="isEdit" placeholder="如 tenant001" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="form.contact_name" placeholder="联系人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" placeholder="联系电话" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="联系邮箱">
          <el-input v-model="form.contact_email" placeholder="联系邮箱" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="详细地址" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="active">正常</el-radio>
            <el-radio value="suspended">暂停</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const tenants = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const currentTenantCode = computed(() => {
  return localStorage.getItem('currentTenantCode') || ''
})

const form = reactive({
  id: null,
  name: '',
  code: '',
  contact_name: '',
  contact_phone: '',
  contact_email: '',
  address: '',
  status: 'active',
})

const rules = {
  name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入租户编码', trigger: 'blur' }],
}

const currentTenant = ref(null)

const loadTenants = async () => {
  loading.value = true
  try {
    const res = await api.get('/tenants')
    tenants.value = res
    // 加载当前租户详情
    const code = currentTenantCode.value
    if (code) {
      const all = res
      const found = all.find(t => t.code === code)
      if (found) {
        try {
          const detail = await api.get(`/tenants/${found.id}`)
          currentTenant.value = detail
        } catch {}
      }
    }
  } catch (e) {
    ElMessage.error('加载租户列表失败')
  } finally {
    loading.value = false
  }
}

const loadTenantDetails = async () => {
  for (const t of tenants.value) {
    try {
      const detail = await api.get(`/tenants/${t.id}`)
      Object.assign(t, detail)
    } catch {}
  }
}

const openCreate = () => {
  isEdit.value = false
  Object.assign(form, {
    id: null, name: '', code: '', contact_name: '',
    contact_phone: '', contact_email: '', address: '', status: 'active',
  })
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    id: row.id, name: row.name, code: row.code,
    contact_name: row.contact_name || '', contact_phone: row.contact_phone || '',
    contact_email: row.contact_email || '', address: row.address || '',
    status: row.status || 'active',
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await api.put(`/tenants/${form.id}`, form)
        ElMessage.success('更新成功')
      } else {
        await api.post('/tenants', form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      await loadTenants()
      await loadTenantDetails()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const switchTenant = async (row) => {
  try {
    const detail = await api.get(`/tenants/${row.id}`)
    localStorage.setItem('currentTenantId', String(row.id))
    localStorage.setItem('currentTenantCode', row.code)
    localStorage.setItem('currentTenantName', row.name)
    currentTenant.value = detail
    ElMessage.success(`已切换到租户：${row.name}`)
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

const deleteTenant = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该租户及其所有数据吗？此操作不可恢复。', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await api.delete(`/tenants/${id}`)
    ElMessage.success('删除成功')
    await loadTenants()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const seedTenants = async () => {
  try {
    await api.post('/tenants/seed')
    ElMessage.success('种子数据初始化完成')
    await loadTenants()
  } catch (e) {
    ElMessage.error('初始化失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  loadTenants()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h3 {
  margin: 0;
  font-size: 18px;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.table-card {
  border: none;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
</style>
