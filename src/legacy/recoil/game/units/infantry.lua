local balance = VFS.Include('gamedata/bfme_balance.lua')
local units = {}
for name, stats in pairs(balance) do
  units[name] = {
    name=name == 'gondor' and 'Gondor Soldier' or 'Mordor Orc',
    description='Original BFME II infantry', objectName=name..'.s3o', script='infantry.lua',
    category='LAND', footprintX=1, footprintZ=1, movementClass='Infantry',
    explodeAs='noweapon', selfDestructAs='noweapon',
    canMove=true, canPatrol=true, canGuard=true, canAttack=true, canStop=true,
    acceleration=.25, brakeRate=.5, speed=name == 'gondor' and 48 or 43,
    turnRate=1400, upright=true, maxSlope=36, maxWaterDepth=8,
    health=stats.health, metalCost=stats.cost/(stats.count or 1), energyCost=0, buildTime=stats.buildTime,
    sightDistance=1100, mass=70, seismicSignature=0,
    collisionVolumeType='CylY', collisionVolumeScales='10 23 10', collisionVolumeOffsets='0 11 0',
    selectionVolumeType='CylY', selectionVolumeScales='15 26 15', selectionVolumeOffsets='0 12 0',
    leaveTracks=false, noAutoFire=false, fireState=2, moveState=1,
    weapons={{def='SWORD', onlyTargetCategory='LAND'}},
    weaponDefs={SWORD={name='Sword', weaponType='Melee', range=27,
      reloadtime=(stats.attackDelayMs or 1000)/1000, damage={default=stats.damage or 12},
      tolerance=18000, turret=true, avoidFriendly=false, collideFriendly=false,
      impulseFactor=0, craterMult=0, areaOfEffect=8}},
    customParams={bfme_name=stats.object, horde_size=stats.count},
  }
end
local function lowerKeys(t)
  local result={}
  for k,v in pairs(t) do
    result[type(k)=='string' and string.lower(k) or k]=type(v)=='table' and lowerKeys(v) or v
  end
  return result
end
return lowerKeys(units)
