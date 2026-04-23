import csv


# write the final aggregated rows to a csv file
def write_csv(rows, output_file, column_order=None):
    # if there are no rows, do nothing
    if not rows:
        return

    # use the provided column order if one is supplied
    fieldnames = column_order or list(rows[0].keys())

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)