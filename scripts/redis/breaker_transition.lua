-- Atomic circuit breaker transition with state validation
-- KEYS[1]: breaker key
-- ARGV[1]: new_state
-- ARGV[2]: failures count
-- ARGV[3]: cooldown_expiry (ms)
-- ARGV[4]: current timestamp (ms)

local key = KEYS[1]
local new_state = ARGV[1]
local failures = tonumber(ARGV[2])
local cooldown_expiry = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local current = redis.call('GET', key)
if current then
    local data = cjson.decode(current)
    -- Prevent illegal transitions
    if data.state == 'OPEN' and new_state ~= 'HALF_OPEN' then
        return {0, 'cannot_transition_from_open', data.state}
    end
    if data.state == 'COOLDOWN' and now < data.cooldown_expiry and new_state ~= 'COOLDOWN' then
        return {0, 'cooldown_active', tostring(data.cooldown_expiry)}
    end
end

local new_data = cjson.encode({
    state = new_state,
    failures = failures,
    cooldown_expiry = cooldown_expiry,
    updated_at = now
})

redis.call('SET', key, new_data)
return {1, 'ok', new_state}
