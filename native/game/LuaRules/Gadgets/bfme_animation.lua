function gadget:GetInfo()
  return {name='BFME original animation bridge', desc='W3D motion channels to native piece transforms',
    author='bfmeXbar', layer=1, enabled=true}
end
if not gadgetHandler:IsSyncedCode() then return end
local clips, tracked = {}, {}
local function applyPose(pieces,pose)
  for bone,p in ipairs(pose) do
    local piece=pieces['bone'..(bone-1)]
    for axis=1,3 do
      Spring.UnitScript.Move(piece,axis,p[axis])
      Spring.UnitScript.Turn(piece,axis,p[axis+3])
    end
  end
end
local function add(id, def)
  local name=UnitDefs[def].name
  if not clips[name] then clips[name]=VFS.Include('animations/'..name..'.lua') end
  local pieces=Spring.GetUnitPieceMap(id)
  tracked[id]={clips=clips[name], pieces=pieces, attack=-100, offset=id%30}
end
function gadget:Initialize()
  GG.BFMEAttack=function(id) if tracked[id] then tracked[id].attack=Spring.GetGameFrame() end end
  for _,id in ipairs(Spring.GetAllUnits()) do add(id,Spring.GetUnitDefID(id)) end
end
function gadget:UnitCreated(id,def) add(id,def) end
function gadget:UnitDestroyed(id) tracked[id]=nil end
function gadget:GameFrame(frame)
  if frame%3~=0 then return end -- 10 Hz pose updates; native simulation stays 30 Hz.
  for id,u in pairs(tracked) do
    local vx,vy,vz=Spring.GetUnitVelocity(id)
    local moving=vx and vx*vx+vz*vz>.025
    local state=moving and 'run' or (frame-u.attack<30 and 'attack' or 'idle')
    local clip=u.clips[state]
    local elapsed=state=='attack' and frame-u.attack or frame+u.offset
    local pose=clip.frames[math.floor(elapsed*clip.fps/30)%#clip.frames+1]
    Spring.UnitScript.CallAsUnit(id,applyPose,u.pieces,pose)
  end
end
