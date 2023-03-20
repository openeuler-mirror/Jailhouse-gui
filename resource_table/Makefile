BUILDDIR = build

CC = gcc

CSRCS += main.c resource_table.c
CSRCS += $(wildcard libfdt/*.c)
CFLAGS += -g -O0

OBJS = $(addprefix $(BUILDDIR)/,$(CSRCS:.c=.o))

.PHONY: all

all: resource-table


resource-table: $(OBJS)
	$(CC) $^ -o $@

$(OBJS): $(BUILDDIR)/%.o : %.c
	test -d $(dir $@) || mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $^ -o $@


.PHONY: clean
clean:
	rm -f $(OBJS)
	rm -f resource-table
