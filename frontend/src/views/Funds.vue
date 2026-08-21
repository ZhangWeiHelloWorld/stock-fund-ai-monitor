<template>
  <div class="funds-page">
    <header class="header">
      <div>
        <h2 class="page-title">基金管理</h2>
        <p class="text-secondary">管理您的基金投资组合</p>
      </div>
      <button class="btn btn-primary" @click="openModal()">
        <span>+ 添加基金</span>
      </button>
    </header>

    <div class="glass-card">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>持仓份额</th>
              <th>成本净值</th>
              <th>持仓状态</th>
              <th>备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fund in funds" :key="fund.id">
              <td>{{ fund.code }}</td>
              <td>{{ fund.name }}</td>
              <td>{{ fund.shares }}</td>
              <td>{{ fund.cost_nav }}</td>
              <td>
                <span class="status-badge" :class="fund.is_holding ? 'active' : 'inactive'">
                  {{ fund.is_holding ? '持仓' : '未持仓' }}
                </span>
              </td>
              <td>{{ fund.note || '-' }}</td>
              <td>
                <div class="actions">
                  <button class="action-btn edit" title="编辑" @click="openModal(fund)">✎</button>
                  <button class="action-btn delete" title="删除" @click="confirmDelete(fund)">🗑</button>
                </div>
              </td>
            </tr>
            <tr v-if="!funds.length">
              <td colspan="7" class="text-center text-secondary">暂无基金数据，请点击右上角添加。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal-content">
        <h3 style="margin-bottom: 20px;">{{ editingFund ? '编辑基金' : '添加基金' }}</h3>
        <form @submit.prevent="saveFund">
          <div class="form-group">
            <label>基金代码</label>
            <input type="text" class="form-control" v-model="form.code" @blur="autoFetchFundName" required placeholder="如：000001">
          </div>
          <div class="form-group">
            <label style="display:flex; justify-content:space-between; align-items:center;">
              <span>基金名称</span>
              <span v-if="fetchingName" style="font-size:0.75rem; color:var(--accent-primary);">查询名称中...</span>
            </label>
            <input type="text" class="form-control" v-model="form.name" placeholder="选填，留空将根据代码自动联想">
          </div>
          <div class="form-group">
            <label>持仓份额</label>
            <input type="number" step="0.01" class="form-control" v-model="form.shares" required>
          </div>
          <div class="form-group">
            <label>成本净值</label>
            <input type="number" step="0.0001" class="form-control" v-model="form.cost_nav" required>
          </div>
          <div class="form-group">
            <label style="display:flex; align-items:center; gap:8px;">
              <input type="checkbox" v-model="form.is_holding">
              当前是否持仓
            </label>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea class="form-control" v-model="form.note" rows="3" placeholder="可选输入备注信息"></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-glass" @click="closeModal">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="loading">
              {{ loading ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import api from '../api'

const showToast = inject('showToast')
const funds = ref([])
const showModal = ref(false)
const editingFund = ref(null)
const loading = ref(false)
const fetchingName = ref(false)

const form = ref({
  code: '',
  name: '',
  shares: 0,
  cost_nav: 0,
  is_holding: true,
  note: ''
})

const autoFetchFundName = async () => {
  const code = (form.value.code || '').trim()
  if (!code || form.value.name) return
  fetchingName.value = true
  try {
    const res = await api.lookupFund(code)
    if (res && res.name) {
      form.value.name = res.name
    }
  } catch (e) {
    console.error(e)
  } finally {
    fetchingName.value = false
  }
}

const fetchFunds = async () => {
  try {
    funds.value = await api.getFunds()
  } catch (e) {
    showToast('加载基金列表失败')
  }
}

const openModal = (fund = null) => {
  editingFund.value = fund
  if (fund) {
    form.value = { ...fund }
  } else {
    form.value = {
      code: '',
      name: '',
      shares: 0,
      cost_nav: 0,
      is_holding: true,
      note: ''
    }
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingFund.value = null
}

const saveFund = async () => {
  loading.value = true
  try {
    if (editingFund.value) {
      await api.updateFund(editingFund.value.id, form.value)
      showToast('✅ 基金已更新')
    } else {
      await api.createFund(form.value)
      showToast('✅ 基金已添加')
    }
    closeModal()
    fetchFunds()
  } catch (e) {
    showToast('❌ 保存失败')
  } finally {
    loading.value = false
  }
}

const confirmDelete = async (fund) => {
  if (confirm(`确定要删除基金【${fund.name}】吗？`)) {
    try {
      await api.deleteFund(fund.id)
      showToast('✅ 基金已删除')
      fetchFunds()
    } catch (e) {
      showToast('❌ 删除失败')
    }
  }
}

onMounted(() => {
  fetchFunds()
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}
.page-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 4px;
}
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}
.status-badge.active {
  background: rgba(0, 255, 136, 0.1);
  color: var(--green);
  border: 1px solid rgba(0, 255, 136, 0.2);
}
.status-badge.inactive {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}
.actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-glass);
  transition: all 0.2s;
}
.action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}
.action-btn.edit:hover { color: var(--accent-primary); }
.action-btn.delete:hover { color: var(--red); }
.text-center { text-align: center; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
