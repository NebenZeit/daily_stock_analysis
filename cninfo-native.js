const http = require('http');
const querystring = require('querystring');

// ==== 关键：600522 正确 orgId ====
const CODE = '600522';
const ORGID = '9900002753';

const postData = querystring.stringify({
  pageNum: 1,
  pageSize: 10,
  tabName: 'fulltext',
  column: 'szse',
  stock: `${CODE},${ORGID}`,
  searchkey: '',
  plate: 'sh',
  category: '',
  seDate: '2025-01-01~2026-06-12',
  sortName: 'time',
  sortType: 'desc',
  isHLtitle: 'true'
});

const options = {
  hostname: 'www.cninfo.com.cn',
  port: 80,
  path: '/new/hisAnnouncement/query',
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Content-Length': Buffer.byteLength(postData),
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'http://www.cninfo.com.cn',
    'Referer': `http://www.cninfo.com.cn/new/disclosure/stock?stockCode=${CODE}&orgId=${ORGID}`,
    'Cookie': 'SID=8fe2c8b0-1f78-4be2-8c4a-c780f514fd6; cninfo_user_browse=600522,9900002753,%E4%B8%AD%E5%A4%A9%A7%91%E6%8A%80',
    'Host': 'www.cninfo.com.cn'
  }
};

const req = http.request(options, (res) => {
  let chunks = [];
  res.on('data', chunk => chunks.push(chunk));
  res.on('end', () => {
    try {
      const result = JSON.parse(Buffer.concat(chunks).toString());
      if (result.announcements && result.announcements.length > 0) {
        console.log(`✅ 共 ${result.totalAnnouncement} 条公告\n`);
        result.announcements.forEach((item, idx) => {
          console.log(`${idx+1}. ${item.announcementTitle}`);
          console.log(`   时间：${new Date(item.announcementTime).toLocaleString()}`);
          console.log(`   PDF：https://static.cninfo.com.cn/${item.adjunctUrl}\n`);
        });
      } else {
        console.log("❌ 无公告数据", result);
      }
    } catch (e) {
      console.error("❌ JSON解析失败", e.message);
    }
  });
});

req.on('error', err => console.error("❌ 请求异常：", err.message));
req.write(postData);
req.end();