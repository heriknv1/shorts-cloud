const API='https://api.github.com';const STUDIO_BRANCH='main';
// One-time logical reset requested on 2026-08-31. Runs before this instant stay in history but no longer consume today's Studio quota.
const QUOTA_RESET_AT=Date.parse('2026-08-31T20:02:00.000Z');
function config(){const token=process.env.GITHUB_PAT,repo=process.env.TARGET_REPO;if(!token||!repo||!repo.includes('/'))throw new Error('Configure GITHUB_PAT e TARGET_REPO na Vercel.');return{token,repo}}
async function gh(path,options={}){const{token}=config();const response=await fetch(`${API}${path}`,{...options,headers:{Accept:'application/vnd.github+json',Authorization:`Bearer ${token}`,'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json',...(options.headers||{})}});if(response.status===204)return null;const text=await response.text();let body=null;try{body=text?JSON.parse(text):null}catch{body=text}if(!response.ok)throw new Error(body?.message||text||`GitHub HTTP ${response.status}`);return body}
function saoPauloDate(iso=new Date().toISOString()){return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(iso))}
async function workflowRuns(){const{repo}=config();return gh(`/repos/${repo}/actions/runs?event=workflow_dispatch&branch=${encodeURIComponent(STUDIO_BRANCH)}&per_page=50`)}
function afterQuotaReset(run){const created=Date.parse(run?.created_at||'');return Number.isFinite(created)&&created>=QUOTA_RESET_AT}
function consumesQuota(run){if(!afterQuotaReset(run)||run.head_branch!==STUDIO_BRANCH)return false;if(run.status!=='completed')return true;return run.conclusion==='success'}
async function usedToday(){const data=await workflowRuns(),today=saoPauloDate();return(data.workflow_runs||[]).filter(r=>saoPauloDate(r.created_at)===today&&consumesQuota(r)).length}
module.exports={gh,config,saoPauloDate,workflowRuns,usedToday,consumesQuota,afterQuotaReset,STUDIO_BRANCH,QUOTA_RESET_AT};