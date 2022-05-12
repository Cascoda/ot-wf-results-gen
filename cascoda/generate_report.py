import math
import os
import re
import sys

import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF


def get_data(filepath="../outputs/hidden_node_simulation_export.csv"):
    df = pd.read_csv(filepath)
    reduced_df = df[
        [
            "%_responded",
            "network_efficiency_%",
            "Node_0_request_stat",
            "Node_2_request_stat",
            "n",
            "t",
            "s",
            "x",
            "p",
        ]
    ]
    sens_pos_df = df[["s", "x"]]

    sim_run = []
    for index, row in reduced_df.iterrows():
        sim_run.append(
            "n="
            + str(row["n"])
            + ", t="
            + str(row["t"])
            + ", s="
            + str(row["s"])
            + ", x="
            + str(row["x"] * 5)
            + ", p="
            + str(row["p"])
        )
    sim_run_df = reduced_df.drop(columns=["n", "t", "s", "x", "p"])
    sim_run_df.insert(0, "sim_run_params", sim_run)

    return reduced_df, sens_pos_df, sim_run_df


def hdp_stats(pdf, col_width, df, sens_pos_df):
    pdf.set_font("helvetica", style="", size=9)
    pdf.multi_cell(
        w=col_width,
        h=5,
        txt="All simulations are run with the following static parameters:",
        border=0,
        ln=2,
    )
    pdf.multi_cell(
        w=col_width,
        h=5,
        txt="  - Number Of Nodes (n) = "
        + str(int(df["n"].unique()[0]))
        + "\n  - Simulation Run Time (t) = "
        + str(int(df["t"].unique()[0]))
        + "\n  - Node 0 Ping (p) = ping ff02::1 "
        + str(int(df["p"].unique()[0]))
        + " 500 0.01 1"
        + "\n  - Node 2 Ping (p) = ping ff02::1 "
        + str(int(df["p"].unique()[0]))
        + " 500 0.01 1"
        + "\n\nHNP = Hidden Node Problem",
        align="L",
        border=0,
        ln=2,
    )
    pdf.cell(w=col_width, h=5, ln=2)
    for sens in sens_pos_df["s"].unique():
        line = (
            "Receive sensitivity (s) "
            + str(sens)
            + " encountered HNP at a linear node distance (x) of "
            + str(sens_pos_df.loc[sens_pos_df["s"] == sens].max()[1] * 5)
            + "."
        )
        pdf.multi_cell(w=col_width, h=5, txt=line, border=0, ln=2)

    return pdf.get_y()


def colored_table(
    pdf,
    headings,
    df,
    x_offset,
    col_width_1,
    reduced_df,
    col_widths=(32, 28, 40, 44, 44),
):
    pdf.set_x(x_offset)
    pdf.set_font("helvetica", style="", size=9)
    # Colors, line width and bold font:
    pdf.set_fill_color(r=255, g=70, b=84)
    pdf.set_text_color(255)
    pdf.set_draw_color(12, 62, 135)
    pdf.set_line_width(0.3)
    pdf.set_font(style="B")
    for col_width, heading in zip(col_widths, headings):
        pdf.cell(col_width, 7, heading, 1, 0, "C", True)
    pdf.ln()
    # Color and font restoration:
    pdf.set_fill_color(224, 235, 255)
    pdf.set_text_color(0)
    pdf.set_font()

    lh_list = []  # list with proper line_height for each row
    use_default_height = 0  # flag
    # create lh_list of line_heights which size is equal to num rows of data
    default_line_height = pdf.font_size
    for index, row in df.iterrows():
        for datum in row:
            word_list = str(datum).split()
            number_of_words = len(word_list)  # how many words
            if (
                number_of_words > 2
            ):  # names and cities formed by 2 words like Los Angeles are ok)
                use_default_height = 1
                new_line_height = pdf.font_size * (
                    number_of_words / 2
                )  # new height change according to data
        if not use_default_height:
            lh_list.append(default_line_height)
        else:
            lh_list.append(new_line_height)
            use_default_height = 0

    fill = False
    for index, row in df.iterrows():
        pdf.set_x(x_offset)
        count = 0
        for col in col_widths:
            line_height = math.floor(lh_list[index])
            pdf.multi_cell(
                w=col,
                h=line_height,
                txt=str(row[count]),
                border="LR",
                ln=3,
                align="C",
                fill=fill,
                max_line_height=pdf.font_size + 1.4,
            )
            count = count + 1
        fill = not fill
        pdf.ln(line_height)
        pdf.set_x(x_offset)
        pdf.cell(sum(col_widths), 0, "", "T")
        if pdf.get_y() >= 190 and not df.shape[0] == (index + 1):
            # pdf.add_page(same=True)
            fill_new_page(pdf, col_width_1, reduced_df)
            pdf.set_xy(x_offset, 10)
            pdf.cell(sum(col_widths), 0, "", "T")


def fill_new_page(pdf, col_width_1, df):
    pdf.add_page(same=True)
    # HND
    pdf.set_font("helvetica", style="I", size=8)
    pdf.cell(txt="Repeated for reference.", ln=1)
    pdf.ln()
    hdp_stats(pdf, col_width_1, df, sens_pos_df)
    # Column break
    pdf.set_xy((10 + col_width_1 + 4), 10)
    pdf.set_fill_color(r=255, g=70, b=84)
    pdf.cell(w=2, h=190, ln=2, txt="", fill=True, border=0)
    pdf.set_fill_color(224, 235, 255)


# used as a key for sorting the plot
def extract_distance(line):
    dis = int(line.split("_")[4].split(".")[0])
    return f"{dis:02}"


def insert_image(pdf, image_dir):
    image_dir_sorted = os.listdir(image_dir)
    image_dir_sorted.sort()
    sorted_files = sorted(
        image_dir_sorted[2:],
        key=lambda x: float(re.findall("(\d+)", x)[0]),  # noqa: W605
    )
    del image_dir_sorted[2:]
    image_dir_sorted = image_dir_sorted + sorted_files
    for file in image_dir_sorted:
        if file.endswith(".png"):
            image = os.path.join(image_dir, file)
            pdf.add_page(same=True)
            pdf.image("assets/A4_background.png", x=0, y=0, w=297)
            pdf.set_font("helvetica", style="B", size=16)
            pdf.set_y(35)
            pdf.cell(w=0, h=10, ln=2, txt=file, border=0, align="C")

            plot_width = 170  # mm
            center_image_x = (297 / 2) - (
                plot_width / 2
            )  # at 72dpi: 1 px = 0.352777778 mm
            center_image_y = 50
            pdf.image(
                image, x=center_image_x, y=center_image_y, w=plot_width
            )  # default image resolution is 72dpi


def make_plots(reduced_df):
    reduced_df["x"] = reduced_df["x"] * 5
    reduced_df = reduced_df.rename(columns={"x": "Node Distance"})
    plot_df = reduced_df[["%_responded", "s", "Node Distance"]].pivot(
        index="s",
        columns="Node Distance",
        values="%_responded",
    )

    plt.rcParams["figure.autolayout"] = True
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    ax = plot_df.plot(title="% Responded against Receive Sensitivity per Node Distance")
    ax.invert_xaxis()
    ax.set_xlabel("Receive Sensitivity")
    ax.set_ylabel("% of requests responded to")
    ax.legend(
        title="Node Distance",
        loc="center left",
        bbox_to_anchor=(1.04, 0.5),
        borderaxespad=0,
    )
    ax.figure.savefig("../outputs/plots/responded_V_rsens_all_nodes.png")

    count = 0
    for column in plot_df:
        plt.clf()
        title = "% Responded against Receive Sensitivity for Node Distance = " + str(
            column
        )
        filename = "../outputs/plots/responded_V_rsens_distance_" + str(column) + ".png"
        ax = plot_df[column].plot(title=title, legend=False, color=colors[count])
        ax.invert_xaxis()
        ax.set_xlabel("Receive Sensitivity")
        ax.set_ylabel("% of requests responded to")
        ax.figure.savefig(filename)
        count = count + 1
    return


def make_pdf(reduced_df, sens_pos_df, sim_run_df):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("helvetica", style="B", size=16)
    pdf.image("assets/A4_background.png", x=0, y=0, w=297)
    pdf.set_auto_page_break(True, margin=1)

    col_width_1 = 80
    col_width_2 = 270 - col_width_1

    # Column break
    pdf.set_xy((10 + col_width_1 + 4), 35)
    pdf.set_fill_color(r=255, g=70, b=84)
    pdf.cell(w=2, h=170, ln=2, txt="", fill=True, border=0)

    # Hidden Node Detected column
    pdf.set_xy(10, 30)
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(w=col_width_1, h=10, ln=2, txt="Hidden Node Detected", border=0)

    hdp_stats(pdf, col_width_1, reduced_df, sens_pos_df)

    # Stats column
    pdf.set_xy((col_width_1 + 20), 30)
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(w=col_width_2, h=10, ln=2, txt="Data Analytics", border=0)

    pdf.set_font("helvetica", style="", size=8)
    pdf.multi_cell(
        w=col_width_2,
        ln=2,
        txt='  - "sim_run_params" represents the simulation parameters,'
        + ' notation described in the "Hidden Node Detected" column.\n'
        + '  - "%_responded" is the percentage of requests responded to.\n'
        + '  - "network_efficiency_%" is the network efficiency'
        + "(central node replies / max theoretical requests).\n"
        + '  - "Node_0_request_stat" is the node 0 number of '
        + "requests sent compared to the number of unique requests.\n"
        + '  - "Node_2_request_stat" is the node 2 number of '
        + "requests sent compared to the number of unique requests.",
        border=0,
        align="L",
        max_line_height=pdf.font_size + 1.4,
    )
    pdf.ln()

    colored_table(
        pdf,
        sim_run_df.columns.values.tolist(),
        sim_run_df,
        (10 + col_width_1 + 10),
        col_width_1,
        reduced_df,
    )

    # Insert images
    make_plots(reduced_df)
    insert_image(pdf, "../outputs/plots/")

    # save pdf
    pdf.output("../outputs/Cascoda_Report.pdf", "F")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        reduced_df, sens_pos_df, sim_run_df = get_data()
    elif str(sys.argv[1]) == "":
        reduced_df, sens_pos_df, sim_run_df = get_data()
    else:
        reduced_df, sens_pos_df, sim_run_df = get_data(str(sys.argv[1]))

    make_pdf(reduced_df, sens_pos_df, sim_run_df)
