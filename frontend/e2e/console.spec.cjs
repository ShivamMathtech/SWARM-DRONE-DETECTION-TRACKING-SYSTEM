const {test,expect}=require('@playwright/test');
test('demo reaches HUD, selection, crop, pause, settings and exports',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.getByText('SYSTEM ONLINE',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'▶ START',exact:true}).click();
 await expect(page.getByRole('button',{name:'Select DR-01',exact:true})).toBeVisible({timeout:45000});
 await page.getByRole('button',{name:'Select DR-01',exact:true}).click();
 await expect(page.locator('.selected-title')).toContainText('DR-01');
 await expect(page.getByLabel('Selected track zoom')).toBeVisible();
 await page.getByLabel('Seeker zoom').selectOption('3');
 await expect.poll(async()=>{const r=await page.request.get('/api/stats');return (await r.json()).frame_id;}).toBeGreaterThan(100);
 await page.getByRole('button',{name:'Ⅱ PAUSE',exact:true}).click();
 await expect(page.getByText('PAUSED · LAST FRAME',{exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/console-preview.png',fullPage:true});
 await page.getByRole('button',{name:'▶ RESUME',exact:true}).click();
 await page.getByRole('button',{name:'■ STOP',exact:true}).click();
 await page.getByRole('button',{name:'SETTINGS ☷',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Settings',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'SAVE PIPELINE SETTINGS',exact:true}).click();
 await page.getByRole('button',{name:'RESEARCH ↗',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Research',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'CSV DETECTIONS ↓'}).first()).toBeVisible();
 await page.getByRole('button',{name:'Close research'}).click();
 expect(errors).toEqual([]);
});

test('uploaded video runs actual YOLO and reaches the frontend canvas',async({page,request})=>{
 // Run python tests/prepare_e2e.py from project root first.
 const before=await request.get('/api/config');const original=await before.json();
 await request.post('/api/stream/stop',{data:{}});
 const configured=await request.post('/api/config',{data:{...original,model_path:'weights/smoke-test.pt',device:'cpu',image_size:320,target_fps:10}});
 expect(configured.ok()).toBeTruthy();
 try{
  await page.goto('/');
  await expect(page.getByText('SYSTEM ONLINE',{exact:true})).toBeVisible();
  await page.locator('#source').selectOption('video');
  await page.locator('input[type="file"]').setInputFiles('../data/smoke.avi');
  await expect(page.getByRole('button',{name:'smoke.avi',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'▶ START',exact:true}).click();
  await expect(page.locator('.top-telemetry.right')).toContainText('smoke-test.pt',{timeout:45000});
  await expect(page.locator('.top-telemetry.left')).toContainText('RUNNING');
  await expect(page.locator('.standby')).toHaveCount(0);
  const pixels=await page.locator('.camera>canvas').evaluate(el=>{const c=el;return Array.from(c.getContext('2d').getImageData(30,150,1,1).data);});
  expect(pixels[3]).toBe(255);
  await expect(page.getByRole('alert')).toHaveCount(0);
 }finally{
  await request.post('/api/stream/stop',{data:{}});
  await request.post('/api/config',{data:original});
 }
});
