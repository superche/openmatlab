c = {[1 2], [3 4 5], 6};
n = cellfun(@numel, c);
s = cellfun(@sum, c);
mx = cellfun(@max, c);
