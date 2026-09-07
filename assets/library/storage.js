(() => {
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function shell(data) {
    return `<section class="panel storage-transfer"><h2>备份、换电脑与更换目录</h2>
      <p>完整备份包含课次、学习证据、偏好、未完成记录和关联项目页。AI 服务仍需联网；这个文件保存的是你的学习档案。</p>
      <div class="storage-actions"><label><input id="backup-live" type="checkbox"> 也保留近期双语转写缓存</label><button class="button" id="download-backup" type="button" ${data.available===false?'disabled':''}>下载完整备份 ZIP</button></div>
      <p class="fine">默认不带完整聊天缓存。Codex 自身聊天记录、录屏、账号和 Skill 程序不在备份里。</p>
      ${data.can_switch===false?'<p>当前是固定目录预览。让 Agent 使用工作区模式启动后，可以在这里切换目录。</p>':`<form id="storage-transfer-form">
      <label for="storage-action">你要做什么</label>
      <select id="storage-action" name="action">
        <option value="move">把当前档案复制到新目录，并使用新目录</option>
        <option value="restore">从备份 ZIP 恢复到一个空目录</option>
        <option value="adopt">使用已复制到本机的学习目录</option>
      </select>
      <div id="backup-file-field" hidden><label for="backup-file">完整学习备份 ZIP</label><input id="backup-file" type="file" accept=".zip,application/zip"></div>
      <label for="storage-destination">目标目录的完整路径</label>
      <input id="storage-destination" name="destination" type="text" required autocomplete="off" placeholder="例如 /Users/你的用户名/Documents/English-Learning">
      <p id="storage-action-help" class="fine">目标必须为空。原目录保留，确认前会检查文件与课次数量。</p>
      <button class="button" type="submit">校验并预览</button>
      </form><div id="storage-plan" hidden></div>`}
      <p id="storage-result" role="status" aria-live="polite"></p>
    </section>`;
  }
  function mount(data) {
    const q=s=>document.querySelector(s), status=q('#storage-result');
    if(!status)return;
    let plan=null;
    async function post(path,body,binary=false) {
      const response=await fetch(path,{method:'POST',
        headers:{'Content-Type':'application/json','X-Coach-Token':data.open_token},
        body:JSON.stringify(body),signal:AbortSignal.timeout(120000)});
      if(!response.ok){const error=await response.json();throw new Error(error.error||'操作未完成');}
      return binary?response.blob():response.json();
    }
    async function run(button,work) {
      if(button.disabled)return;
      button.disabled=true;status.textContent='正在校验本地文件，请稍等…';
      try{await work();}catch(error){status.textContent=error.message;}
      finally{button.disabled=false;}
    }
    q('#download-backup').addEventListener('click',e=>run(e.currentTarget,async()=>{
      const blob=await post('/api/storage/backup',{include_live:q('#backup-live').checked},true);
      const url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download='english-learning-'+new Date().toISOString().slice(0,10)+'.zip';
      document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
      status.textContent='完整备份已交给浏览器下载。换电脑时，选择“从备份 ZIP 恢复”，也可以让 Agent 代为恢复。';
    }));
    const form=q('#storage-transfer-form');if(!form)return;
    const action=q('#storage-action'),preview=q('#storage-plan');
    function invalidate(){plan=null;preview.hidden=true;}
    form.addEventListener('input',invalidate);
    action.addEventListener('change',()=>{
      invalidate();q('#backup-file-field').hidden=action.value!=='restore';
      q('#storage-action-help').textContent=action.value==='adopt'
        ?'选择已经复制到本机的完整学习目录。不会把两套记录合并；当前旧目录保留。'
        :'目标必须为空。原目录保留，确认前会检查文件与课次数量。';
    });
    form.addEventListener('submit',e=>{
      e.preventDefault();const button=form.querySelector('button[type="submit"]');
      run(button,async()=>{
        invalidate();
        const body={action:action.value,destination:q('#storage-destination').value.trim()};
        if(body.action==='restore'){
          const file=q('#backup-file').files[0];if(!file)throw new Error('请选择完整备份 ZIP。');
          if(file.size>data.transfer_limit_bytes)throw new Error('文件超过网页恢复上限，请让 Agent 校验并复制。');
          const bytes=new Uint8Array(await file.arrayBuffer());let raw='';
          for(let i=0;i<bytes.length;i+=8192)raw+=String.fromCharCode(...bytes.subarray(i,i+8192));
          body.backup_base64=btoa(raw);
        }
        const result=await post('/api/storage/preview',body);
        plan=result.plan;
        preview.innerHTML=`<h3>确认使用这个目录</h3><code>${esc(result.destination)}</code>
          <p>${result.counts.sessions} 次练习 · ${result.counts.expressions} 条表达 · ${result.counts.concepts} 个知识点</p>
          <p>${esc(result.message)}</p><button id="apply-storage" class="button primary" type="button">确认切换到这个目录</button>`;
        preview.hidden=false;status.textContent='校验完成；尚未切换。';
        q('#apply-storage').addEventListener('click',e=>run(e.currentTarget,async()=>{
          if(!plan)throw new Error('预览已失效，请重新校验。');
          const result=await post('/api/storage/apply',{plan});
          status.textContent=result.message;
          location.reload();
        }));
      });
    });
  }
  window.CoachStorage={shell,mount};
})();
