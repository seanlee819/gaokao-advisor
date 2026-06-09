const api = require('../../utils/api')

Page({
  data: {
    provinces: [],
    provinceIdx: 0,
    categories: ['理科', '文科', '综合', '物理类', '历史类'],
    category: '理科',
    score: '',
    rank: '',
    canSubmit: false,
    loading: false,
    user: null
  },

  onLoad() {
    this.updateUser()
    api.getProvinces().then(res => {
      this.setData({ provinces: res.provinces || [] })
    }).catch(() => {
      this.setData({
        provinces: ['北京','天津','河北','山西','内蒙古','辽宁','吉林','黑龙江',
                    '上海','江苏','浙江','安徽','福建','江西','山东','河南',
                    '湖北','湖南','广东','广西','海南','重庆','四川','贵州',
                    '云南','西藏','陕西','甘肃','青海','宁夏','新疆']
      })
    })
  },

  onShow() {
    this.updateUser()
  },

  updateUser() {
    const app = getApp()
    this.setData({ user: app.globalData.user || null })
  },

  onProvinceChange(e) {
    this.setData({ provinceIdx: parseInt(e.detail.value) })
  },

  onCategoryChange(e) {
    this.setData({ category: e.detail.value })
  },

  onScoreInput(e) {
    this.setData({ score: e.detail.value })
    this.checkSubmit()
  },

  onRankInput(e) {
    this.setData({ rank: e.detail.value })
    this.checkSubmit()
  },

  checkSubmit() {
    const { score, rank, provinces, provinceIdx } = this.data
    this.setData({
      canSubmit: score > 0 && rank > 0 && provinces.length > 0
    })
  },

  onRecommend() {
    const { score, rank, provinces, provinceIdx, category } = this.data
    const province = provinces[provinceIdx]

    if (!score || !rank) {
      wx.showToast({ title: '请输入分数和位次', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    api.recommend({
      score: parseInt(score),
      rank: parseInt(rank),
      province,
      category,
      top_n: 20
    }).then(res => {
      this.setData({ loading: false })
      // 保存查询历史
      this.saveHistory(province, category, score, rank, res)
      wx.navigateTo({
        url: `/pages/result/result?data=${encodeURIComponent(JSON.stringify(res))}`
      })
    }).catch(err => {
      this.setData({ loading: false })
      wx.showToast({ title: err.detail || err.msg || '查询失败', icon: 'none' })
    })
  },

  goMine() {
    wx.switchTab({ url: '/pages/mine/mine' })
  },

  saveHistory(province, category, score, rank, result) {
    const history = wx.getStorageSync('query_history') || []
    history.unshift({
      time: new Date().toLocaleString(),
      province, category, score, rank,
      summary: result.summary,
      data: JSON.stringify(result)
    })
    // Keep last 20
    if (history.length > 20) history.pop()
    wx.setStorageSync('query_history', history)
  }
})
