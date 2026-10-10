"""Summarize/plot a real native camera trace (optional matplotlib==3.10.7)."""

from common.paths import ROOT
import argparse
import csv
import json
import math
from pathlib import Path


def load(path):
    with Path(path).open(newline='') as stream:
        rows=[{key:float(value) for key,value in row.items()} for row in csv.DictReader(stream)]
    rendered=[row for row in rows if row['phase']==3 and
              all(math.isfinite(row[key]) for key in ('camera_x','camera_y','camera_z','back_z','elevation_degrees'))]
    # Exclude loading-screen camera setup. The regression starts its sweep at 300.
    start=next((row['seconds'] for row in rendered if row['target_height']==300),
               rendered[0]['seconds'] if rendered else 0)
    rendered=[row for row in rendered if row['seconds']>=start]
    for row in rendered:
        row['elapsed']=row['seconds']-start
        z=row['camera_z']-row['focus_z']
        distance=z/row['back_z'] if abs(row['back_z'])>.001 else 0
        row['pivot_error']=math.hypot(row['camera_x']-row['back_x']*distance-row['focus_x'],
                                      row['camera_y']-row['back_y']*distance-row['focus_y'])
        row['height_above_focus']=z
    native=[row for row in rows if row['phase']==1 and row['seconds']>=start and math.isfinite(row['camera_z'])]
    summary={'samples':len(rows),'rendered_frames':len(rendered),
             'duration_seconds':rendered[-1]['elapsed'] if rendered else 0,
             'phase_names':{'0':'before native view update','1':'native camera transform',
                            '2':'after view update','3':'rendered frame'},
             'native_previous_height_max_difference':max((abs(row['camera_z']-row['focus_z']-row['current_height']) for row in native),default=0),
             'minimum_camera_height_above_focus':min((row['height_above_focus'] for row in rendered),default=0),
             'maximum_pivot_error_world_units':max((row['pivot_error'] for row in rendered),default=0),
             'maximum_angle_step_degrees':max((abs(b['elevation_degrees']-a['elevation_degrees']) for a,b in zip(rendered,rendered[1:])),default=0),
             'projection_switches':[]}
    for before,after in zip(rendered,rendered[1:]):
        if before['projection']!=after['projection']:
            summary['projection_switches'].append({'seconds':after['elapsed'],'projection':int(after['projection']),
                'angle_step_degrees':after['elevation_degrees']-before['elevation_degrees'],
                'pivot_error':after['pivot_error']})
    return rendered,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',type=Path)
    parser.add_argument('--before',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rows,summary=load(args.trace)
    if not rows:raise SystemExit('No valid rendered frames in trace')
    before=[]
    if args.before:before,summary['before']=load(args.before)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,1,figsize=(12,11),sharex=True,layout='constrained')
    fig.suptitle('bmfe-workshop — recorded camera movement',fontsize=18,weight='bold')
    t=[row['elapsed'] for row in rows]
    axes[0].plot(t,[r['target_height'] for r in rows],label='Requested height',color='#89929b',ls='--')
    axes[0].plot(t,[r['filtered_height'] for r in rows],label='Measured native height',color='#027a90')
    axes[0].set_ylabel('Zoom height\n(world units)');axes[0].legend(loc='upper right')
    axes[1].plot(t,[r['elevation_degrees'] for r in rows],color='#027a90',label='Rendered elevation')
    axes[1].set_ylabel('Camera elevation\n(degrees)');axes[1].set_ylim(30,95)
    for a,b in zip(rows,rows[1:]):
        if b['projection']==1:axes[1].axvspan(a['elapsed'],b['elapsed'],color='#bcdfc2',alpha=.18,lw=0)
    axes[1].text(.01,.92,'Green = orthographic',transform=axes[1].transAxes,fontsize=9)
    axes[2].plot(t,[r['pivot_error'] for r in rows],color='#027a90',label='After correction')
    if before:axes[2].plot([r['elapsed'] for r in before],[r['pivot_error'] for r in before],color='#c64b43',alpha=.7,label='Before correction')
    axes[2].set_ylabel('Aim-point drift\n(world units)');axes[2].legend(loc='upper right')
    axes[3].plot(t,[r['scaled_bar_width'] for r in rows],color='#027a90',label='Scaled width')
    axes[3].plot(t,[r['native_bar_width'] for r in rows],color='#89929b',ls='--',label='Original width')
    axes[3].set_ylabel('Last health bar\n(pixels)');axes[3].set_xlabel('Seconds from first zoom-in command')
    axes[3].legend(loc='upper right')
    for ax in axes:ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    fig.savefig(args.output.with_suffix('.png'),dpi=150)
    plt.close(fig)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
