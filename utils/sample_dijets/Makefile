PYTHIA8 ?= $(PYTHIA8DIR)
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2

all: sample_dijets

sample_dijets: sample_dijets.cpp
	@test -n "$(PYTHIA8)" || { echo "PYTHIA8 not set (activate the chain conda env or pass PYTHIA8=/path/to/pythia8316)"; exit 1; }
	$(CXX) $(CXXFLAGS) $< -o $@ \
	  -I$(PYTHIA8)/include -L$(PYTHIA8)/lib -Wl,-rpath,$(PYTHIA8)/lib -lpythia8 -lm

clean:
	rm -f sample_dijets

.PHONY: all clean
