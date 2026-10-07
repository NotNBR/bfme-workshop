local root = piece('root')
function script.Create() end
function script.QueryWeapon() return root end
function script.AimFromWeapon() return root end
function script.AimWeapon() return true end
function script.FireWeapon()
  if GG.BFMEAttack then GG.BFMEAttack(unitID) end
end
function script.Killed() return 0 end
