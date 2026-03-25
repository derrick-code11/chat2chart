import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const BRAND_PALETTE = ["#107A4D", "#4A9A7A", "#C4D8CB", "#2563EB", "#7C3AED", "#F59E0B"];

function getColors(spec) {
  return spec?.style?.palette?.length ? spec.style.palette : BRAND_PALETTE;
}

const TICK = { fontSize: 11, fill: "#6B6B6B", fontFamily: "Inter, sans-serif" };
const GRID = { strokeDasharray: "3 3", stroke: "#E4E0DA" };
const MARGIN = { top: 8, right: 12, left: 0, bottom: 4 };
const TOOLTIP_CONTENT = {
  backgroundColor: "#fff",
  border: "1px solid #E4E0DA",
  borderRadius: 4,
  fontSize: 12,
  fontFamily: "Inter, sans-serif",
  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
};

function BarView({ spec }) {
  const { encoding, data } = spec;
  const xField = encoding.x.field;
  const yField = encoding.y.field;
  const colors = getColors(spec);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data.rows} margin={MARGIN}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey={xField} tick={TICK} tickLine={false} axisLine={{ stroke: "#E4E0DA" }} />
        <YAxis tick={TICK} tickLine={false} axisLine={false} width={44} />
        <Tooltip contentStyle={TOOLTIP_CONTENT} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
        <Bar dataKey={yField} fill={colors[0]} radius={[3, 3, 0, 0]} maxBarSize={56} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function LineView({ spec }) {
  const { encoding, data } = spec;
  const xField = encoding.x.field;
  const yField = encoding.y.field;
  const colors = getColors(spec);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data.rows} margin={MARGIN}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey={xField} tick={TICK} tickLine={false} axisLine={{ stroke: "#E4E0DA" }} />
        <YAxis tick={TICK} tickLine={false} axisLine={false} width={44} />
        <Tooltip contentStyle={TOOLTIP_CONTENT} />
        <Line
          type="monotone"
          dataKey={yField}
          stroke={colors[0]}
          strokeWidth={2}
          dot={{ r: 3, fill: colors[0], strokeWidth: 0 }}
          activeDot={{ r: 5, strokeWidth: 0 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function PieView({ spec }) {
  const { encoding, data } = spec;
  const labelField = (encoding.label ?? encoding.x).field;
  const valueField = (encoding.value ?? encoding.y).field;
  const colors = getColors(spec);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data.rows}
          dataKey={valueField}
          nameKey={labelField}
          cx="50%"
          cy="48%"
          outerRadius={95}
          innerRadius={38}
          paddingAngle={2}
        >
          {data.rows.map((_, i) => (
            <Cell key={i} fill={colors[i % colors.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_CONTENT}
          formatter={(value, name) => [value, name]}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, fontFamily: "Inter, sans-serif" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function StackedBarView({ spec }) {
  const { encoding, data } = spec;
  const xField = encoding.x.field;
  const seriesField = encoding.series.field;
  const yField = encoding.y.field;
  const colors = getColors(spec);

  const seriesValues = [...new Set(data.rows.map((r) => String(r[seriesField])))];
  const pivotMap = {};
  for (const row of data.rows) {
    const x = String(row[xField]);
    if (!pivotMap[x]) pivotMap[x] = { [xField]: x };
    pivotMap[x][String(row[seriesField])] = row[yField];
  }
  const chartData = Object.values(pivotMap);

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={MARGIN}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey={xField} tick={TICK} tickLine={false} axisLine={{ stroke: "#E4E0DA" }} />
        <YAxis tick={TICK} tickLine={false} axisLine={false} width={44} />
        <Tooltip contentStyle={TOOLTIP_CONTENT} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
        <Legend
          iconType="square"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, fontFamily: "Inter, sans-serif" }}
        />
        {seriesValues.map((s, i) => (
          <Bar key={s} dataKey={s} stackId="a" fill={colors[i % colors.length]} maxBarSize={56} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

const VIEWS = { bar: BarView, line: LineView, pie: PieView, stacked_bar: StackedBarView };

export default function ChartCard({ spec }) {
  if (!spec) return null;

  const View = VIEWS[spec.type];
  if (!View) {
    return (
      <p style={{ fontSize: 13, color: "#6B6B6B" }}>Unknown chart type: {spec.type}</p>
    );
  }

  return (
    <div>
      {spec.title && (
        <p
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "#2A2A2A",
            letterSpacing: "-0.01em",
            marginBottom: spec.subtitle ? 2 : 10,
          }}
        >
          {spec.title}
        </p>
      )}
      {spec.subtitle && (
        <p style={{ fontSize: 11, color: "#9A9A8A", marginBottom: 10 }}>{spec.subtitle}</p>
      )}
      <View spec={spec} />
    </div>
  );
}
