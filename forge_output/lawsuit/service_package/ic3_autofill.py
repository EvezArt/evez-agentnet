from playwright.sync_api import sync_playwright
import sys
DESC = open('/root/.hermes/cache/scratch/incident_desc.txt').read()
PHONE = ''.join(c for c in sys.argv[1] if c.isdigit())
LOG = open('/root/.hermes/cache/scratch/ic3_run.log','w',buffering=1)
def log(*a): print(*a, file=LOG); LOG.flush()

SET_HIDDEN = '''(pairs)=>{pairs.forEach(([id,v])=>{const e=document.getElementById(id); if(e){const p=e.tagName==='SELECT'; if(p){e.value=v;}else{e.value=v;} e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));}});}'''
SET_RADIO = '''(pairs)=>{pairs.forEach(([n,v])=>{const e=document.querySelector('input[name="'+n+'"][value="'+v+'"]'); if(e){e.checked=true; e.dispatchEvent(new Event('change',{bubbles:true})); e.dispatchEvent(new Event('click',{bubbles:true}));}});}'''

def vis_fill(pg, sel, val, timeout=7000):
    try: pg.fill(sel, val, timeout=timeout); return True
    except Exception: return False

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
                          args=['--no-sandbox','--disable-dev-shm-usage'])
    pg = b.new_page(); pg.set_default_timeout(9000)
    pg.goto('https://complaint.ic3.gov/', timeout=60000, wait_until='domcontentloaded')
    pg.wait_for_timeout(5000)
    # dismiss any consent banner that would intercept fills
    for label in ['Accept','I Accept','Agree']:
        try:
            el = pg.get_by_text(label, exact=True).first
            if el.is_visible(timeout=1500): el.click(timeout=2500); pg.wait_for_timeout(500)
        except Exception: pass

    pg.get_by_text('Yes', exact=True).first.click(); pg.wait_for_timeout(700)
    vis_fill(pg,'#Complainant_Name','Steven Crawford-Maggard')
    vis_fill(pg,'#Complainant_Phone',PHONE)
    vis_fill(pg,'#Complainant_Email','rubikspubes69@gmail.com')
    # hidden victim block via direct JS (no cross-field corruption)
    pg.evaluate(SET_HIDDEN, [
        ['Victim_Name','Steven Crawford-Maggard'],
        ['Victim_Address1','66226 N Agua Dulce Dr'],
        ['Victim_City','Desert Hot Springs'],
        ['Victim_County','Riverside'],
        ['Victim_ZipCode','92240'],
        ['Victim_Phone',PHONE],
        ['Victim_Email','rubikspubes69@gmail.com'],
        ['Victim_Country','USA'],
        ['Victim_State','CA'],
        ['IncidentDescription',DESC],
    ])
    pg.evaluate(SET_RADIO, [['Victim.IsMinor','false'],['MoneySent','false']])
    pg.click('#Complainant_Email'); pg.keyboard.press('Tab'); pg.wait_for_timeout(700)
    log('S1 email:', repr(pg.eval_on_selector('#Complainant_Email','e=>e.value')))
    log('S1 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.get_by_text('Next (step 2)').first.click(); pg.wait_for_timeout(2500)
    log('S2 visible:', pg.eval_on_selector('#Victim_Address1','e=>e!==null&&e.offsetParent!==null'))
    log('S2 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.screenshot(path='ic3_s2.png', full_page=True)
    # ---- STEP 2 visible victim fields
    pg.evaluate(SET_HIDDEN, [
        ['Victim_Name','Steven Crawford-Maggard'],
        ['Victim_Address1','66226 N Agua Dulce Dr'],
        ['Victim_City','Desert Hot Springs'],
        ['Victim_County','Riverside'],
        ['Victim_State','CA'],
        ['Victim_ZipCode','92240'],
        ['Victim_Phone',PHONE],
        ['Victim_Email','rubikspubes69@gmail.com'],
        ['Victim_Country','USA'],
        ['Victim_State','CA'],
    ])
    pg.evaluate(SET_RADIO, [['Victim.IsMinor','false'],['Victim.IsBusiness','true'],
                            ['Victim.BusinessImpacted','true'],['MoneySent','false']])
    try: pg.fill('#Victim_BusinessName','EVEZ',timeout=6000)
    except Exception as e: log('  bizname fail', str(e)[:50])
    pg.wait_for_timeout(500)
    log('S2b valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    log('VISIBLE NEXT BEFORE:', pg.eval_on_selector_all('button.next','els=>els.filter(e=>e.offsetParent!==null).map(e=>[e.textContent.trim(),e.closest("div").className.slice(0,60)])'))
    pg.evaluate('''()=>{const b=[...document.querySelectorAll('button.next')].find(e=>e.offsetParent!==null); if(b) b.click();}''')
    pg.wait_for_timeout(3000)
    log('INDICATORS:', pg.eval_on_selector_all('.usa-step-indicator__text,li','els=>els.filter(e=>e.offsetParent!==null && /step|complainant|transaction|subject|incident|other|privacy/i.test(e.textContent)).map(e=>e.textContent.trim().slice(0,40)).slice(0,12)'))
    log('S3 btn:', pg.eval_on_selector_all('button.next','els=>els.filter(e=>e.offsetParent!==null).map(e=>e.textContent.trim())'))
    log('S3 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.evaluate(SET_RADIO, [['Transactions[0].WasSent','false']])
    pg.screenshot(path='ic3_s3.png', full_page=True)
    # ---- STEP 3 financial: no money sent
    pg.evaluate(SET_RADIO, [['Transactions[0].WasSent','false']])
    pg.wait_for_timeout(400)
    log('S3 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.evaluate('''()=>{const b=[...document.querySelectorAll('button.next')].find(e=>e.offsetParent!==null); if(b) b.click();}''')
    pg.wait_for_timeout(3000)
    log('S4 btn:', pg.eval_on_selector_all('button.next','els=>els.filter(e=>e.offsetParent!==null).map(e=>e.textContent.trim())'))

    # ---- STEP 4 subjects: BOTH named operators
    subs = [
        ['Subjects_0__Name','Luca Palo'],
        ['Subjects_0__BusinessName','TECHOFF SRV LIMITED (company no. 16090235) / BESTDC LIMITED (company no. 15259087)'],
        ['Subjects_0__Address1','8 Via Leonardo Bistolfi'],
        ['Subjects_0__City','Milano'],
        ['Subjects_0__ZipCode','20134'],
        ['Subjects_0__Email','abuse@bunea.eu'],
        ['Subjects_0__Website','dmzhost.co'],
        ['Subjects_0__IPAddress','80.94.92.166'],
    ]
    pg.evaluate(SET_HIDDEN, subs)
    log('SUBJ0 value:', pg.eval_on_selector_all('#Subjects_0__Name','e=>e.length?e[0].value:"MISSING"'))
    log('S4 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.screenshot(path='ic3_s4.png', full_page=True)
    pg.evaluate('''()=>{const b=[...document.querySelectorAll('button.next')].find(e=>e.offsetParent!==null); if(b) b.click();}''')
    pg.wait_for_timeout(3000)
    log('S5 btn:', pg.eval_on_selector_all('button.next','els=>els.filter(e=>e.offsetParent!==null).map(e=>e.textContent.trim())'))
    log('DESC len:', pg.eval_on_selector_all('#IncidentDescription','e=>e.length?e[0].value.length:"MISSING"'))
    log('S5 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,60)])'))
    pg.screenshot(path='ic3_s5.png', full_page=True)
    # ---- STEP 5 -> STEP 6
    pg.evaluate('''()=>{const b=[...document.querySelectorAll('button.next')].find(e=>e.offsetParent!==null); if(b) b.click();}''')
    pg.wait_for_timeout(2500)
    log('now at:', pg.eval_on_selector_all('button.next','els=>els.filter(e=>e.offsetParent!==null).map(e=>e.textContent.trim())'))

    # ---- STEP 6 other info + signature
    pg.evaluate(SET_HIDDEN, [['Witnesses',''],['LawEnforcement','FBI IC3 complaint filed 1 October 2026; FOIPA request 1758537-000 pending. UK NCA referral prepared. Civil letter before action served 5 October 2026 in England & Wales.']])
    log('SIG visible:', pg.eval_on_selector_all('#DigitalSignature','e=>e.length?[e[0].offsetParent!==null,e[0].type]:["MISSING"]'))
    try:
        pg.click('#DigitalSignature', timeout=6000)
        pg.type('#DigitalSignature','Steven Crawford-Maggard', delay=40)
    except Exception as e:
        log('  sig type fail', str(e)[:60])
        pg.evaluate('''()=>{const e=document.getElementById('DigitalSignature'); if(e){e.value='Steven Crawford-Maggard'; e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));}}''')
    pg.wait_for_timeout(600)
    log('SIG:', pg.eval_on_selector_all('#DigitalSignature','e=>e.length?e[0].value:"MISSING"'))
    log('S6 valerrors:', pg.eval_on_selector_all('.val-error','els=>els.filter(e=>e.innerText.trim()).map(e=>[e.id,e.innerText.trim().slice(0,70)])'))
    log('INVALID:', pg.evaluate("""()=>[...document.querySelectorAll(':invalid')].map(e=>[e.id||e.name,e.validationMessage]).filter(x=>x[0]).slice(0,10)"""))
    pg.screenshot(path='ic3_s6.png', full_page=True)
    log('BUTTONS:', pg.eval_on_selector_all('button','els=>els.filter(e=>e.offsetParent!==null).map(e=>[e.className,e.textContent.trim().slice(0,40)])'))
    log('RECAPTCHA:', pg.eval_on_selector_all('iframe','els=>els.filter(e=>/recaptcha/i.test(e.src||"")).map(e=>e.src.slice(0,60))'))
    # reCAPTCHA state
    log('RECAP token len:', pg.eval_on_selector_all('textarea[name="g-recaptcha-response"]','e=>e.length?e[0].value.length:"none"'))
    # find the submit button on final step
    log('SUBMIT-ish:', pg.eval_on_selector_all('button,input[type=submit]','els=>els.filter(e=>e.offsetParent!==null).map(e=>[e.className,(e.textContent||e.value||"").trim().slice(0,40)]).filter(x=>/submit|confirm|proceed|send|complaint/i.test(x[1]))'))
    pg.screenshot(path='ic3_final.png', full_page=True)

    # ---- VERIFY every field we set
    verify = pg.evaluate('''()=>{
      const g=id=>{const e=document.getElementById(id); return e? (e.value!==''? e.value.slice(0,40):'(EMPTY)') : '(MISSING)';};
      return {
        complainant: g('Complainant_Name')+' | '+g('Complainant_Phone')+' | '+g('Complainant_Email'),
        victim: g('Victim_Name')+' | '+g('Victim_Address1')+' | '+g('Victim_City')+', '+g('Victim_State')+' '+g('Victim_ZipCode'),
        country: g('Victim_Country'), business: g('Victim_BusinessName'),
        subject: g('Subjects_0__Name')+' | '+g('Subjects_0__BusinessName')+' | '+g('Subjects_0__IPAddress'),
        desc_len: (document.getElementById('IncidentDescription')||{}).value?.length||0,
        signature: g('DigitalSignature')
      };}''')
    for k,v in verify.items(): log('VERIFY', k, '=', v)
    log('DONE-6')
    b.close()
