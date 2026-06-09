Page({
  data: {
    info: {},
    chong: [],
    wen: [],
    bao: [],
    activeTab: 'chong',
    displayList: [],
    tagClass: 'chong',
    tagText: '冲刺'
  },

  onLoad(options) {
    try {
      const raw = decodeURIComponent(options.data || '{}')
      const data = JSON.parse(raw)
      this.setData({
        info: data.my_info || {},
        chong: data['冲'] || [],
        wen: data['稳'] || [],
        bao: data['保'] || [],
        displayList: data['冲'] || []
      })
      this.updateTag()
    } catch (e) {
      wx.showToast({ title: '数据解析失败', icon: 'none' })
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      activeTab: tab,
      displayList: this.data[tab] || []
    })
    this.updateTag()
  },

  updateTag() {
    const tab = this.data.activeTab
    const map = {
      chong: { tagClass: 'chong', tagText: '冲刺' },
      wen: { tagClass: 'wen', tagText: '匹配' },
      bao: { tagClass: 'bao', tagText: '保底' }
    }
    this.setData(map[tab] || map.chong)
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    const { province, category } = this.data.info
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}&province=${province}&category=${category}`
    })
  }
})
