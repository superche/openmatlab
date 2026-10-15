classdef SignalDemo < handle
  % Event/listener demo (O-E7).
  properties
    count = 0
  end
  events
    Ping
  end
  methods
    function ping(obj)
      notify(obj, 'Ping');
    end
    function delete(obj)
      fprintf('SignalDemo closed\n');
    end
  end
end
