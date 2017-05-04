/*
 * Code to aid in the rendering of 3D models. Some models will have spatial references
 * to some global coordinate system or "world position". These coordinate systems may
 * make it hard for a user to interact with a model. To address this problem, the
 * "view_changed()" function sets the center-of-rotation for the model to a position
 * determined by where X3Dom renders the model. This makes it easier to interact with
 * a model, no matter where it is located in its own world position / global coordinate
 * system.
 */
   
var start_center_rotation = null;
var last_ray_pos = {x: null, y: null, z: null};

function modelOnLoad(){
    // do this once the model has loaded
    if(document.getElementById('x3dom')){
        var xdom = document.getElementById('x3dom');
        xdom.runtime.ready();
        xdom.runtime.showAll();
        
        if(document.getElementById('preview-1-file-panel-title')){
            // change the title of the panel to show it's a 3D model
            var act_dom = document.getElementById('preview-1-file-panel-title');
            act_dom.innerHTML = 'Interactive 3D Model';
        }
    
        if(document.getElementById('preview-1-file-pttl-l-span')){
            var act_dom = document.getElementById('preview-1-file-pttl-l-span');
            var html = [
                //'<button type="button" class="btn btn-default btn-xs" ',
                // 'style="margin-bottom: 5px;" ',
                '<a title="Reset and Re-center the 3D model view" ',
                'href="javascript:resetModelView();" >',
                '<i class="fa fa-refresh" aria-hidden="true"></i>',
                ' Reset + Center View',
                '</a>'
            ].join('\n');
            act_dom.innerHTML = html;
        }
        
        if(document.getElementById('x3dviewpoint')){
            var vp_dom = document.getElementById('x3dviewpoint');
            vp_dom.addEventListener("viewpointChanged", view_changed, false);
        }
    }
}
  
function view_changed(e){
   
    if (start_center_rotation === null){
        // set center of rotation
        var xdom = document.getElementById('x3dom');
        var scene = document.getElementById('x3dScene');
      
        var dims = {
            w: xdom.runtime.getWidth(),
            h: xdom.runtime.getHeight()
        };
        
        console.log(dims);
        var c_w = xdom.runtime.getCameraToWorldCoordinatesMatrix();
        var vp = xdom.runtime.viewpoint();
        var origin = new x3dom.fields.SFVec3f(0, 0, 0);
        var wt = xdom.runtime.getCurrentTransform(scene);
        var o_pos = wt.multMatrixPnt(origin);
        var center_pos = c_w.multFullMatrixPnt(o_pos);
        // center_pos.z = center_pos.z * .99;
        vp.setCenterOfRotation(center_pos);
        start_center_rotation = vp.getCenterOfRotation();
      
        // it sometimes takes time for a scene to fully render.
        // to see if it has, make a ray to get it's "world position"
        // if the world position has settled down and doens't change much,
        // we've got our center of rotation finalzed.
        // other wise, we set the start_center_rotation to null so this function will run again
        // to recalculate as the scene rendering continues.
        var canvas_pos = xdom.runtime.calcCanvasPos(start_center_rotation.x,
                                                    start_center_rotation.y,
                                                    start_center_rotation.z);
        var ray =  xdom.runtime.getViewingRay(canvas_pos[0], canvas_pos[1]);
        console.log(canvas_pos);
        console.log(ray);
        if(check_different_values(ray.pos.x, last_ray_pos.x)){
            start_center_rotation = null;
        }
        if(check_different_values(ray.pos.y, last_ray_pos.y)){
            start_center_rotation = null;
        }
        if(check_different_values(ray.pos.z, last_ray_pos.z)){
            start_center_rotation = null;
        }
        last_ray_pos = {x: ray.pos.x, y: ray.pos.y, z: ray.pos.z};
        console.log(start_center_rotation);
    }
   
  }

function check_different_values(current, last){
    // checks to see if the current and last values differ enough to be
    // considered different
    var different = true;
    var ok_dif = current * 0.05;
    var low_cur = current - ok_dif;
    var high_cur = current + ok_dif;
    if(last >= low_cur && last <= high_cur){
        different = false;
    }
    else{
        different = true;
    }
    return different;
}
  
function resetModelView(){
    var xdom = document.getElementById('x3dom');
    console.log('Reset View fired');
    // console.log(xdom.runtime);
    xdom.runtime.showAll();
    return false;
}
 