<template>
  <div class="stocks-page">
    <header class="header">
      <div>
        <h2 class="page-title">股票管理</h2>
        <p class="text-secondary">管理您的股票投资组合</p>
      </div>
      <button class="btn btn-primary" @click="openModal()">
        <span>+ 添加股票</span>
      </button>
    </header>

    <div class="glass-card">
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>持仓股数</th>
              <th>成本单价</th>
              <th>持仓状态</th>
              <th>备注</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stock in stocks" :key="stock.id">
              <td>{{ stock.code }}</td>
              <td>{{ stock.name }}</td>
              <td>{{ stock.shares }}</td>
              <td>{{ stock.cost_price }}</td>
              <td>
                <span class="status-badge" :class="stock.is_holding ? 'active' : 'inactive'">
                  {{ stock.is_holding ? '持仓' : '未持仓' }}
                </span>
              </td>
              <td>{{ stock.note || '-' }}</td>
              <td>
                <div class="actions">
                  <button class="action-btn edit" title="编辑" @click="openModal(stock)">✎</button>
                  <button class="action-btn delete" title="删除" @click="confirmDelete(stock)">🗑</button>
                </div>
              </td>
            </tr>
            <tr v-if="!stocks.length">
              <td colspan="7" class="text-center text-secondary">暂无股票数据，请点击右上角添加。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" :class="{ active: showModal }">
      <div class="modal-content">
        <h3 style="margin-bottom: 20px;">{{ editingStock ? '编辑股票' : '添加股票' }}</h3>
        <form @submit.prevent="saveStock">
          <div class="form-group">
            <label>股票代码</label>
            <input type="text" class="form-control" v-model="form.code" @blur="autoFetchStockName" required placeholder="如：sh600519 或 600519">
          </div>
          <div class="form-group">
            <label style="display:flex; justify-content:space-between; align-items:center;">
              <span>股票名称</span>
              <span v-if="fetchingName" style="font-size:0.75rem; color:var(--accent-primary);">查询名称中...</span>
            </label>
            <input type="text" class="form-control" v-model="form.name" placeholder="选填，留空将根据代码自动联想">
          </div>
          <div class="form-group">
            <label>持仓股数</label>
            <input type="number" class="form-control" v-model="form.shares" required>
          </div>
          <div class="form-group">
            <label>成本单价</label>
            <input type="number" step="0.001" class="form-control" v-model="form.cost_price" required>
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
const stocks = ref([])
const showModal = ref(false)
const editingStock = ref(null)
const loading = ref(false)
const fetchingName = ref(false)

const form = ref({
  code: '',
  name: '',
  shares: 0,
  cost_price: 0,
  is_holding: true,
  note: ''
})

const autoFetchStockName = async () => {
  const code = (form.value.code || '').trim()
  if (!code || form.value.name) return
  fetchingName.value = true
  try {
    const res = await api.lookupStock(code)
    if (res && res.name) {
      form.value.name = res.name
    }
  } catch (e) {
    console.error(e)
  } finally {
    fetchingName.value = false
  }
}

const fetchStocks = async () => {
  try {
    stocks.value = await api.getStocks()
  } catch (e) {
    showToast('加载股票列表失败')
  }
}

const openModal = (stock = null) => {
  editingStock.value = stock
  if (stock) {
    form.value = { ...stock }
  } else {
    form.value = {
      code: '',
      name: '',
      shares: 0,
      cost_price: 0,
      is_holding: true,
      note: ''
    }
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingStock.value = null
}

const saveStock = async () => {
  loading.value = true
  try {
    if (editingStock.value) {
      await api.updateStock(editingStock.value.id, form.value)
      showToast('✅ 股票已更新')
    } else {
      await api.createStock(form.value)
      showToast('✅ 股票已添加')
    }
    closeModal()
    fetchStocks()
  } catch (e) {
    showToast('❌ 保存失败')
  } finally {
    loading.value = false
  }
}

const confirmDelete = async (stock) => {
  if (confirm(`确定要删除股票【${stock.name}】吗？`)) {
    try {
      await api.deleteStock(stock.id)
      showToast('✅ 股票已删除')
      fetchStocks()
    } catch (e) {
      showToast('❌ 删除失败')
    }
  }
}

onMounted(() => {
  fetchStocks()
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
