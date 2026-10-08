-- Minimal native LuaUI. Recoil retains selection, orders, pathfinding and camera input.
local test=Spring.GetModOptions().autotest=='1'
local strategic=false
local captured={}
local startTimer=0
local function camera(x,z,height)
  Spring.SetCameraState({mode=1,px=x,py=Spring.GetGroundHeight(x,z),pz=z,height=height,angle=1,flipped=-1},0)
end
function Initialize()
  Spring.SendCommands({'viewta','minimap geo 0.80 0.03 0.18 0.24','showhealthbars 1','disticon 180','resbar 0','info 0','tooltip 0','console 0'})
  camera(1800,2048,950)
end
function DrawScreen()
  local w,h=Spring.GetViewGeometry()
  gl.Color(.035,.05,.055,.9); gl.Rect(20,h-113,610,h-20)
  gl.Color(.93,.79,.47,1); gl.Text('bfmeXbar  /  NATIVE RECOIL',36,h-49,23,'o')
  gl.Color(.84,.88,.87,1)
  gl.Text('BFME II  |  Gondor vs Mordor  |  '..#Spring.GetTeamUnits(0)..' allies',36,h-73,14,'o')
  gl.Text('Drag select  /  Right-click move or attack  /  Shift queue',36,h-94,13,'o')
  gl.Color(.035,.05,.055,.9); gl.Rect(20,20,750,66)
  gl.Color(.9,.91,.86,1)
  gl.Text('Wheel: zoom  |  Tab: strategic view  |  B: battalion  |  Space: focus  |  A: attack-move',34,39,14,'o')
  gl.Color(1,1,1,1)
end
function KeyPress(key,mods,isRepeat)
  if isRepeat then return false end
  if key==9 then
    strategic=not strategic
    camera(2048,2048,strategic and 4600 or 1000)
    return true
  elseif key==32 then
    local ids=Spring.GetSelectedUnits()
    if #ids>0 then
      local x,y,z=Spring.GetUnitPosition(ids[1]); camera(x,z,500)
    end
    return true
  elseif key==98 then
    local groups={}
    for _,id in ipairs(Spring.GetSelectedUnits()) do
      local group=Spring.GetUnitRulesParam(id,'battalion')
      if group then groups[group]=true end
    end
    local selected={}
    for _,id in ipairs(Spring.GetTeamUnits(Spring.GetMyTeamID())) do
      if groups[Spring.GetUnitRulesParam(id,'battalion')] then selected[#selected+1]=id end
    end
    Spring.SelectUnitArray(selected)
    return true
  end
  return false
end
function GameFrame(frame)
  if not test then return end
  if frame==30 then camera(1600,2048,230) end
  if frame==90 or frame==900 or frame==1800 then
    if frame==900 then camera(2048,2048,650) end
    if frame==1800 then camera(2048,2048,4600) end
    captured[frame]=true
  end
  if frame==100 or frame==920 or frame==1820 then Spring.SendCommands('screenshot png') end
  if frame==2750 then Spring.SendCommands('quitforce') end
end
function GameOver()
  if test then Spring.SendCommands('quitforce') end
end
function GameSetup() return true,true end
function Update(dt)
  if Spring.GetGameFrame()<0 then
    startTimer=startTimer+dt
    if startTimer>2 then Spring.SendCommands('forcestart'); startTimer=0 end
  end
end
Initialize()
