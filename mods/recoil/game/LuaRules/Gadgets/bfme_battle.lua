function gadget:GetInfo()
  return {name='bmfe-workshop battle', desc='Native armies and battle verification', author='bmfe-workshop', layer=0, enabled=true}
end
if not gadgetHandler:IsSyncedCode() then return end
local options=Spring.GetModOptions()
local size=math.max(20,math.min(1500,tonumber(options.armysize) or 525))
local test=options.autotest=='1'
local damage, deaths, moved=0,0,0
local movementSeen=false
local origins={}
local function spawn(team,name,x,heading,hordeSize)
  local columns=math.ceil(math.sqrt(size))
  for i=0,size-1 do
    local px=x+(i%columns)*19
    local pz=2048+(math.floor(i/columns)-columns/2)*19
    local id=Spring.CreateUnit(name,px,Spring.GetGroundHeight(px,pz),pz,heading,team)
    if id then
      origins[id]={px,pz}
      Spring.SetUnitRulesParam(id,'battalion',math.floor(i/hordeSize)+team*10000,{inlos=true})
      if team==1 or test then Spring.GiveOrderToUnit(id,CMD.FIGHT,{team==0 and 2500 or 1350,0,2048},0) end
    end
  end
end
function gadget:GameStart()
  Spring.SetTeamResource(0,'m',10000); Spring.SetTeamResource(0,'e',10000)
  spawn(0,'gondor',1400,1,15); spawn(1,'mordor',2300,3,20)
  Spring.Echo('BFX_NATIVE_START units='..#Spring.GetAllUnits()..' engine='..Engine.version)
end
function gadget:UnitDamaged(id,def,team,amount) damage=damage+amount end
function gadget:UnitDestroyed(id) deaths=deaths+1; origins[id]=nil end
function gadget:GameFrame(frame)
  if frame%300==0 then
    moved=0
    for id,p in pairs(origins) do
      local x,y,z=Spring.GetUnitPosition(id)
      if x and (x-p[1])^2+(z-p[2])^2>100 then moved=moved+1 end
    end
    Spring.SetGameRulesParam('bfx_deaths',deaths)
    movementSeen=movementSeen or moved>0
    Spring.SetGameRulesParam('bfx_damage',damage)
    Spring.Echo(string.format('BFX_NATIVE_TICK frame=%d units=%d moved=%d damage=%.1f deaths=%d',frame,#Spring.GetAllUnits(),moved,damage,deaths))
  end
  if test and frame==(tonumber(options.testframes) or 2700) then
    Spring.Echo(damage>0 and deaths>0 and movementSeen and 'BFX_NATIVE_TEST_PASS' or 'BFX_NATIVE_TEST_FAIL')
    Spring.GameOver({})
  end
end
